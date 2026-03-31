"""Excel 上传、异步处理与结果下载 API。"""

from __future__ import annotations

import os
import threading
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.config import RESULTS_DIR, UPLOADS_DIR, Country as CountryEnum
from app.models.excel import (
    AnalysisResult,
    ColorDistribution,
    JobStatusResponse,
    ProcessRequest,
    ProcessResult,
    ProcessStartResponse,
    ResultsListResponse,
    ResultFileInfo,
    UploadResponse,
    UploadedFilesResponse,
)

router = APIRouter(prefix="/api/excel", tags=["excel"])

MAX_UPLOAD_SIZE = int(os.getenv("EXCEL_MAX_UPLOAD_SIZE", str(25 * 1024 * 1024)))
READ_CHUNK_SIZE = 1024 * 1024
LISTINGS_EXTENSIONS = {".txt", ".tsv", ".csv"}
CATEGORY_EXTENSIONS = {".xlsx", ".xlsm", ".xls"}
JOB_STATES: dict[str, dict[str, Any]] = {}
JOB_LOCK = threading.Lock()


def _safe_filename(filename: str) -> str:
    cleaned = Path(filename or "").name.strip().replace(" ", "_")
    if not cleaned:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    return cleaned


def _validate_extension(filename: str, allowed_extensions: set[str], file_label: str) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise HTTPException(
            status_code=400,
            detail=f"{file_label} 仅支持以下格式: {allowed}",
        )


def _resolve_country(country: str) -> CountryEnum:
    normalized = str(country or "").strip().upper()
    try:
        return CountryEnum(normalized)
    except ValueError as exc:
        supported = ", ".join(item.value for item in CountryEnum)
        raise HTTPException(
            status_code=400,
            detail=f"不支持的国家代码: {country}. 支持: {supported}",
        ) from exc


async def _save_upload(
    *,
    upload: UploadFile,
    destination: Path,
    allowed_extensions: set[str],
    file_label: str,
) -> str:
    original_name = _safe_filename(upload.filename or "")
    _validate_extension(original_name, allowed_extensions, file_label)

    total_size = 0
    try:
        with destination.open("wb") as output:
            while True:
                chunk = await upload.read(READ_CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_SIZE:
                    output.close()
                    destination.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"上传文件过大，限制为 {MAX_UPLOAD_SIZE // (1024 * 1024)} MB",
                    )
                output.write(chunk)
    finally:
        await upload.close()

    return original_name


def _create_upload_path(country: CountryEnum, prefix: str, original_name: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return UPLOADS_DIR / f"{country.value}_{prefix}_{timestamp}_{original_name}"


def _list_uploaded_files(country: CountryEnum, prefix: str) -> list[str]:
    files = sorted(
        (path for path in UPLOADS_DIR.glob(f"{country.value}_{prefix}_*") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return [path.name for path in files]


def _extract_original_upload_name(path: Path, country: CountryEnum, prefix: str) -> str | None:
    marker = f"{country.value}_{prefix}_"
    if not path.name.startswith(marker):
        return None

    remainder = path.name[len(marker) :]
    if len(remainder) <= 15 or remainder[14] != "_":
        return None

    timestamp = remainder[:14]
    if not timestamp.isdigit():
        return None

    return remainder[15:]


def _cleanup_old_uploads(
    country: CountryEnum,
    prefix: str,
    keep_path: Path,
    *,
    keep_latest_only: bool = True,
) -> None:
    keep_original_name = _extract_original_upload_name(keep_path, country, prefix)

    for path in UPLOADS_DIR.glob(f"{country.value}_{prefix}_*"):
        if not path.is_file() or path == keep_path:
            continue

        if not keep_latest_only:
            if keep_original_name is None:
                continue

            original_name = _extract_original_upload_name(path, country, prefix)
            if original_name != keep_original_name:
                continue

        path.unlink(missing_ok=True)


def _resolve_uploaded_file(filename: str) -> Path:
    safe_name = _safe_filename(filename)
    file_path = UPLOADS_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"上传文件不存在: {safe_name}")
    return file_path


def _result_filename(filename: str) -> str:
    """结果文件名：只做路径截断，不替换空格（结果文件名由系统生成，允许含空格）。"""
    name = Path(filename or "").name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    return name


def _resolve_result_file(filename: str) -> Path:
    safe_name = _result_filename(filename)
    file_path = RESULTS_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"结果文件不存在: {safe_name}")
    return file_path


def _create_listing_indexer() -> Any:
    try:
        from app.core.indexers import ListingIndex  # type: ignore[attr-defined]

        return ListingIndex()
    except (ImportError, AttributeError):
        from app.core.indexers import ListingIndexer

        return ListingIndexer()


def _analyze_all_listings(file_path: Path) -> AnalysisResult:
    try:
        indexer = _create_listing_indexer()
        index_data = indexer.build_index([file_path], [])
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="All listings 文件编码不正确，请使用 UTF-8 导出") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"解析 all listings 失败: {exc}") from exc

    prefixes = sorted(
        {
            row["parsed_sku"].product_code
            for row in index_data["all_listings_rows"]
            if row.get("parsed_sku") is not None and row["parsed_sku"].product_code is not None
        }
    )
    suffixes = sorted(
        {
            row["parsed_sku"].suffix
            for row in index_data["all_listings_rows"]
            if row.get("parsed_sku") is not None and row["parsed_sku"].suffix is not None
        }
    )
    color_counter = Counter(
        row["parsed_sku"].color_code
        for row in index_data["all_listings_rows"]
        if row.get("parsed_sku") is not None and row["parsed_sku"].color_code is not None
    )
    color_distribution = [
        ColorDistribution(color_code=color_code, count=count)
        for color_code, count in sorted(color_counter.items())
        if color_code is not None
    ]

    return AnalysisResult(
        success=True,
        filename=file_path.name,
        total_skus=index_data["stats"]["all_listings_count"],
        prefixes=prefixes,
        suffixes=suffixes,
        color_distribution=color_distribution,
        unique_colors=len(color_distribution),
        unknown_colors=[],
    )


def _create_processor() -> Any:
    try:
        from app.core.processors.add_color_size_processor import AddColorSizeProcessor

        return AddColorSizeProcessor()
    except ImportError as exc:
        raise RuntimeError(f"无法加载 AddColorSizeProcessor: {exc}") from exc


def _normalize_process_output(result: Any) -> ProcessResult:
    if isinstance(result, ProcessResult):
        return result

    if isinstance(result, tuple):
        if len(result) == 2:
            output_file, processed_count = result
            skipped_count = 0
        elif len(result) >= 3:
            output_file, processed_count, skipped_count = result[:3]
        else:
            raise RuntimeError("处理器返回了无效结果")
        return ProcessResult(
            output_file=str(output_file),
            processed_count=int(processed_count),
            skipped_count=int(skipped_count),
        )

    if isinstance(result, dict):
        output_file = (
            result.get("output_file")
            or result.get("output_filename")
            or result.get("filename")
        )
        if not output_file:
            raise RuntimeError("处理器未返回 output_file")
        return ProcessResult(
            output_file=str(output_file),
            processed_count=int(result.get("processed_count", 0)),
            skipped_count=int(result.get("skipped_count", 0)),
        )

    output_file = getattr(result, "output_file", None) or getattr(result, "output_filename", None)
    if output_file:
        return ProcessResult(
            output_file=str(output_file),
            processed_count=int(getattr(result, "processed_count", 0)),
            skipped_count=int(getattr(result, "skipped_count", 0)),
        )

    raise RuntimeError("无法识别处理器返回结果")


def _set_job_state(job_id: str, **updates: Any) -> None:
    with JOB_LOCK:
        job = JOB_STATES.get(job_id)
        if job is None:
            return
        job.update(updates)


def _run_process_job(job_id: str, request: ProcessRequest) -> None:
    _set_job_state(job_id, status="running", progress=5, error=None)

    try:
        processor = _create_processor()
        _set_job_state(job_id, progress=15)

        process_method = getattr(processor, "process", None)
        if process_method is None:
            raise RuntimeError("AddColorSizeProcessor 缺少 process 方法")

        try:
            raw_result = process_method(request, progress_callback=lambda p: _set_job_state(job_id, progress=max(15, min(int(p), 95))))
        except TypeError:
            raw_result = process_method(request)

        result = _normalize_process_output(raw_result)
        output_path = RESULTS_DIR / _result_filename(result.output_file)
        if not output_path.exists():
            raise RuntimeError(f"处理完成但结果文件不存在: {result.output_file}")

        _set_job_state(job_id, status="completed", progress=100, result=result)
    except HTTPException as exc:
        _set_job_state(job_id, status="failed", progress=100, error=exc.detail)
    except NotImplementedError as exc:
        _set_job_state(job_id, status="failed", progress=100, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        _set_job_state(job_id, status="failed", progress=100, error=f"处理失败: {exc}")


def _validate_process_files(request: ProcessRequest) -> None:
    if request.input_mode == "matrix":
        if not request.selected_prefixes:
            raise HTTPException(status_code=400, detail="matrix 模式下 selected_prefixes 不能为空")
        if not request.target_colors:
            raise HTTPException(status_code=400, detail="matrix 模式下 target_colors 不能为空")
        if not request.start_size or not request.end_size:
            raise HTTPException(status_code=400, detail="matrix 模式下 start_size 和 end_size 不能为空")
    elif request.input_mode == "direct-sku" and not request.direct_skus:
        raise HTTPException(status_code=400, detail="direct-sku 模式下 direct_skus 不能为空")

    for filename in request.all_listings_files:
        all_listings_path = _resolve_uploaded_file(filename)
        if f"{request.country.value}_all_listings_" not in all_listings_path.name:
            raise HTTPException(status_code=400, detail=f"all_listings_files 与国家不匹配: {filename}")

    if request.fr_all_listings_file and request.country in {CountryEnum.DE, CountryEnum.IT, CountryEnum.ES}:
        fr_all_listings_path = _resolve_uploaded_file(request.fr_all_listings_file)
        if "FR_all_listings_" not in fr_all_listings_path.name:
            raise HTTPException(status_code=400, detail="fr_all_listings_file 必须是 FR all listings 文件")

    for filename in request.category_files:
        category_path = _resolve_uploaded_file(filename)
        if f"{request.country.value}_category_" not in category_path.name:
            raise HTTPException(status_code=400, detail=f"category 文件与国家不匹配: {filename}")


@router.post("/upload/listings", response_model=AnalysisResult)
async def upload_listings(
    file: UploadFile = File(...),
    country: str = Form(...),
) -> AnalysisResult:
    """上传 all listings 文件并返回分析结果。"""
    resolved_country = _resolve_country(country)
    original_name = _safe_filename(file.filename or "")
    destination = _create_upload_path(resolved_country, "all_listings", original_name)
    await _save_upload(
        upload=file,
        destination=destination,
        allowed_extensions=LISTINGS_EXTENSIONS,
        file_label="all listings 文件",
    )
    _cleanup_old_uploads(
        resolved_country,
        "all_listings",
        destination,
        keep_latest_only=False,
    )
    return _analyze_all_listings(destination)


@router.post("/upload/category", response_model=UploadResponse)
async def upload_category(
    file: UploadFile = File(...),
    country: str = Form(...),
    store_type: str = Form(...),
) -> UploadResponse:
    """上传 category 文件。"""
    resolved_country = _resolve_country(country)
    normalized_store_type = str(store_type or "").strip().lower()
    if normalized_store_type not in {"pz", "ep"}:
        raise HTTPException(status_code=422, detail="store_type must be 'pz' or 'ep'")

    prefix = f"category_{normalized_store_type}"
    original_name = _safe_filename(file.filename or "")
    destination = _create_upload_path(resolved_country, prefix, original_name)
    await _save_upload(
        upload=file,
        destination=destination,
        allowed_extensions=CATEGORY_EXTENSIONS,
        file_label="category 文件",
    )
    _cleanup_old_uploads(
        resolved_country,
        prefix,
        destination,
        keep_latest_only=False,
    )
    return UploadResponse(success=True, filename=destination.name)


@router.get("/files", response_model=UploadedFilesResponse)
async def get_uploaded_files(country: CountryEnum = Query(...)) -> UploadedFilesResponse:
    """按国家列出已上传文件。"""
    return UploadedFilesResponse(
        all_listings=_list_uploaded_files(country, "all_listings"),
        pz_category_listings=_list_uploaded_files(country, "category_pz"),
        ep_category_listings=_list_uploaded_files(country, "category_ep"),
    )


@router.delete("/files/uploaded")
async def delete_uploaded_file(filename: str = Query(...)) -> dict[str, Any]:
    """删除已上传文件。"""
    file_path = _resolve_uploaded_file(filename)
    file_path.unlink()
    return {"success": True, "filename": filename}


@router.post("/process", response_model=ProcessStartResponse)
async def process_excel(request: ProcessRequest) -> ProcessStartResponse:
    """创建后台处理任务。"""
    _validate_process_files(request)

    job_id = uuid.uuid4().hex
    with JOB_LOCK:
        JOB_STATES[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "progress": 0,
            "result": None,
            "error": None,
            "created_at": datetime.now(),
        }

    thread = threading.Thread(target=_run_process_job, args=(job_id, request), daemon=True)
    thread.start()
    return ProcessStartResponse(job_id=job_id, status="pending")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """查询处理任务状态。"""
    with JOB_LOCK:
        job = JOB_STATES.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"任务不存在: {job_id}")
        result = job.get("result")

    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=int(job["progress"]),
        result=result,
        error=job.get("error"),
    )


@router.get("/download/{filename}")
async def download_result(filename: str) -> FileResponse:
    """下载处理结果文件。"""
    file_path = _resolve_result_file(filename)
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/results", response_model=ResultsListResponse)
async def list_results() -> ResultsListResponse:
    """列出结果目录中的文件。"""
    files = sorted(
        (path for path in RESULTS_DIR.iterdir() if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return ResultsListResponse(
        files=[
            ResultFileInfo(
                filename=path.name,
                modified_at=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(
                    microsecond=0
                ),
            )
            for path in files
        ]
    )
