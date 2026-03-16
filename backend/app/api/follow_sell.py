"""跟卖上新 API 路由。"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import RESULTS_DIR
from app.core.processors.follow_sell_processor import FollowSellProcessor
from app.models.follow_sell import (
    FollowSellJobStatus,
    FollowSellRequest,
    FollowSellResult,
)

router = APIRouter(prefix="/api/follow-sell", tags=["follow-sell"])

JOB_STATES: dict[str, dict[str, Any]] = {}
JOB_LOCK = threading.Lock()


def _result_filename(filename: str) -> str:
    name = Path(filename or "").name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    return name


@router.post("/process", response_model=FollowSellJobStatus)
async def start_follow_sell(request: FollowSellRequest) -> FollowSellJobStatus:
    """触发异步跟卖处理任务，返回 job_id。"""
    try:
        request.validate_category_count()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    job_id = str(uuid.uuid4())
    with JOB_LOCK:
        JOB_STATES[job_id] = {
            "status": "pending",
            "progress": 0,
            "result": None,
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def _run():
        with JOB_LOCK:
            JOB_STATES[job_id]["status"] = "running"

        def _progress(pct: int) -> None:
            with JOB_LOCK:
                JOB_STATES[job_id]["progress"] = pct

        try:
            result = FollowSellProcessor().process(request, progress_callback=_progress)
            with JOB_LOCK:
                JOB_STATES[job_id].update(
                    status="completed",
                    progress=100,
                    result=result.model_dump(),
                )
        except Exception as exc:  # noqa: BLE001
            with JOB_LOCK:
                JOB_STATES[job_id].update(status="failed", error=str(exc))

    threading.Thread(target=_run, daemon=True).start()
    return FollowSellJobStatus(job_id=job_id, status="pending", progress=0)


@router.get("/status/{job_id}", response_model=FollowSellJobStatus)
async def get_job_status(job_id: str) -> FollowSellJobStatus:
    """轮询任务状态。"""
    with JOB_LOCK:
        raw = JOB_STATES.get(job_id)
        state = dict(raw) if raw is not None else None
    if state is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {job_id}")

    result = None
    if state.get("result"):
        result = FollowSellResult(**state["result"])

    return FollowSellJobStatus(
        job_id=job_id,
        status=state["status"],
        progress=state["progress"],
        result=result,
        error=state.get("error"),
    )


@router.get("/download/{filename}")
async def download_result(filename: str) -> FileResponse:
    """下载结果文件。"""
    safe_name = _result_filename(filename)
    file_path = RESULTS_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"结果文件不存在: {safe_name}")
    return FileResponse(
        path=file_path,
        filename=safe_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
