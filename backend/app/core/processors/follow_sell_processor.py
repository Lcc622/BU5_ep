# backend/app/core/processors/follow_sell_processor.py
"""跟卖上新处理器。"""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from openpyxl import load_workbook

from app.config import (
    COUNTRY_PROFILES, RESULTS_DIR, TEMPLATES_DIR, UPLOADS_DIR, Country,
)
from app.core.indexers.listing_indexer import ListingIndexer
from app.core.parsers.sku import parse_sku
from app.models.follow_sell import FollowSellRequest, FollowSellResult


MAPPING_FILENAME = "新老款映射信息(1).xlsx"


def normalize_sku_input(raw: str, country: Any) -> str:
    from app.config import Country as _C
    stripped = raw.strip()
    if country == _C.UK:
        return stripped.rstrip("+")
    return stripped

IMAGE_COLUMNS = [
    "main_image_url",
    "other_image_url1", "other_image_url2", "other_image_url3",
    "other_image_url4", "other_image_url5", "other_image_url6",
    "other_image_url7", "other_image_url8",
]


def build_fr_asin_index(fr_listings_path: Path) -> dict[str, str]:
    """从法国 All Listings 构建 {sku_upper: asin} 映射。"""
    indexer = ListingIndexer()
    index = indexer.build_index([fr_listings_path], [])
    by_sku: dict[str, Any] = index.get("by_sku", {}) if isinstance(index, dict) else {}
    fr_asin_map: dict[str, str] = {}

    for raw_sku, entry in by_sku.items():
        if not isinstance(entry, dict):
            continue
        flat = entry.get("merged_data") or entry.get("all_listings_data") or {}
        asin = str(flat.get("asin1") or flat.get("product-id") or "").strip()
        sku = str(raw_sku or flat.get("seller-sku") or flat.get("sku") or "").strip().upper()
        if sku and asin:
            fr_asin_map[sku] = asin

    return fr_asin_map


def load_product_mapping(mapping_path: Path | None = None) -> dict[str, str]:
    """加载新老款产品码对照表。

    Returns:
        {new_product_code: old_product_code}
    """
    path = mapping_path or (UPLOADS_DIR / MAPPING_FILENAME)
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    mapping: dict[str, str] = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        old_code = str(row[0] or "").strip().upper()
        new_code = str(row[1] or "").strip().upper()
        if old_code and new_code:
            mapping[new_code] = old_code
    wb.close()
    return mapping


def scan_old_skus_by_prefix(
    index: dict[str, Any],
    old_product_code: str,
    color_code: str,
) -> list[dict[str, Any]]:
    """在 by_sku 索引中按前缀扫描老款 SKU 行，返回 merged_data 平铺字典列表。"""
    prefix = (old_product_code + color_code).upper()
    by_sku: dict[str, Any] = index.get("by_sku", {}) if isinstance(index, dict) else {}
    results = []
    for raw_sku, entry in by_sku.items():
        upper_sku = raw_sku.upper()
        if not upper_sku.startswith(prefix):
            continue
        # TODO: UK risk pending confirmation - does UK All Listings contain old product code + -UK1 suffix SKUs? If yes, need to restore '-' filter for UK.
        if not isinstance(entry, dict):
            continue
        flat = entry.get("merged_data") or entry.get("all_listings_data") or {}
        if flat:
            results.append(flat)
    return results


def build_new_sku(
    old_info: Any,
    old_product_code: str,
    new_product_code: str,
    target_suffix: str | None,
) -> str:
    """使用老款解析结果重建新 SKU，并应用目标后缀。"""
    return f"{new_product_code.upper()}{old_info.color_code}{old_info.size_code}{target_suffix or ''}"


def calculate_prices(old_price: Any) -> tuple[float, float]:
    """计算新版本售价和 RRP。

    Raises:
        ValueError: 老款价格缺失或无法解析
    """
    if old_price is None or str(old_price).strip() == "":
        raise ValueError("老款 price 缺失，无法计算新价格")
    try:
        base = round(float(old_price), 2)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"老款 price 无法解析: {old_price!r}") from exc
    new_price = round(base + 0.1, 2)
    list_price = round(new_price + 10, 2)
    return new_price, list_price


def _resolve_template_path(template_file: str) -> Path:
    """解析模板路径，兼容 Docker 和本地开发环境。"""
    docker_path = TEMPLATES_DIR / template_file
    if docker_path.exists():
        return docker_path
    local_path = Path(__file__).resolve().parents[4] / "templates" / template_file
    if local_path.exists():
        return local_path
    raise FileNotFoundError(
        f"模板文件不存在: {template_file}\n"
        f"  尝试路径 1: {docker_path}\n"
        f"  尝试路径 2: {local_path}"
    )


def _write_to_template(
    template_path: Path,
    output_path: Path,
    rows: list[dict[str, Any]],
) -> None:
    """将行数据写入 Excel 模板（复用 UK AddColor 模板结构）。"""
    if not template_path.exists():
        raise FileNotFoundError(f"模板文件不存在: {template_path}")

    shutil.copy(template_path, output_path)
    wb = load_workbook(output_path)
    ws = wb.active

    max_col = ws.max_column
    display_headers = {
        str(ws.cell(2, c).value or "").strip().casefold(): c
        for c in range(1, max_col + 1)
    }
    machine_headers = {
        str(ws.cell(3, c).value or "").strip().casefold(): c
        for c in range(1, max_col + 1)
    }

    def _col_idx(key: str) -> int | None:
        k = key.strip().casefold()
        # 优先匹配机器列名，fallback 显示列名；
        # 同时尝试 hyphen ↔ underscore 互转，兼容 All Listings 连字符字段名
        return (
            machine_headers.get(k)
            or display_headers.get(k)
            or machine_headers.get(k.replace("-", "_"))
            or machine_headers.get(k.replace("_", "-"))
            or display_headers.get(k.replace("-", "_"))
        )

    # 模板 row 4 开始为数据区（含示例行），从 row 4 开始写以覆盖示例数据
    START_ROW = 4
    # 先清空模板已有的示例数据行（row 4 开始）
    for r in range(START_ROW, ws.max_row + 1):
        for c in range(1, max_col + 1):
            ws.cell(row=r, column=c, value=None)

    for row_idx, row_data in enumerate(rows, start=START_ROW):
        for field_key, value in row_data.items():
            col = _col_idx(field_key)
            if col is not None:
                ws.cell(row=row_idx, column=col, value=value)

    wb.save(output_path)
    wb.close()


class FollowSellProcessor:
    """跟卖上新处理器。"""

    def process(
        self,
        request: FollowSellRequest,
        progress_callback: Callable[[int], None] | None = None,
    ) -> FollowSellResult:
        def _progress(pct: int) -> None:
            if progress_callback:
                progress_callback(pct)

        _progress(5)

        # 1. 加载映射表
        mapping = load_product_mapping()
        if not mapping:
            raise RuntimeError("映射文件为空或不存在，请确认 backend/uploads/新老款映射信息(1).xlsx")

        _progress(10)

        # 2. 构建索引
        indexer = ListingIndexer()
        listings_paths = [UPLOADS_DIR / filename for filename in request.all_listings_files]
        category_paths = [UPLOADS_DIR / f for f in request.category_files]
        index = indexer.build_index(listings_paths, category_paths)
        if request.country in {Country.DE, Country.IT, Country.ES} and request.fr_all_listings_file:
            fr_asin_map = build_fr_asin_index(UPLOADS_DIR / request.fr_all_listings_file)
        else:
            fr_asin_map = {}

        _progress(30)

        # 3. 解析新款 SKU → 按 (new_product_code, color_code) 分组
        color_groups: dict[tuple[str, str], str] = {}  # (new_pc, color) -> suffix
        invalid_skus: list[str] = []
        for raw in request.new_skus:
            try:
                normalized = normalize_sku_input(raw, request.country)
                info = parse_sku(normalized)
            except (ValueError, Exception):
                invalid_skus.append(raw)
                continue
            key = (info.product_code, info.color_code)
            if key not in color_groups:
                color_groups[key] = info.suffix

        _progress(40)

        # 4. 对每个颜色组生成行
        profile = COUNTRY_PROFILES[request.country]
        all_rows: list[dict[str, Any]] = []
        skipped_skus: list[str] = []
        no_price_skus: list[str] = []
        identity_skus: list[str] = []

        total_groups = len(color_groups)
        for idx, ((new_pc, color_code), suffix) in enumerate(color_groups.items()):
            old_pc = mapping.get(new_pc)
            if old_pc is None:
                skipped_skus.append(f"{new_pc}{color_code}{suffix}（映射表无此产品码）")
                continue
            if old_pc == new_pc:
                identity_skus.append(new_pc)

            old_rows = scan_old_skus_by_prefix(index, old_pc, color_code)
            if not old_rows:
                skipped_skus.append(f"{new_pc}{color_code}{suffix}（All Listings 无老款命中）")
                continue

            # 找同色组内有 Category 数据的"参考行"，用于补全无 Category 数据的行
            # 优先从老款 SKU（无后缀）中找；若全无，则回退到新款 SKU（含 '-' 后缀）
            reference_row = next(
                (r for r in old_rows if index.get("by_sku", {}).get(
                    str(r.get("seller-sku") or "").strip().upper(), {}
                ).get("category_data") is not None),
                None,
            )
            if reference_row is None:
                cat_prefix = (old_pc + color_code).upper()
                for _sku_key, _entry in index.get("by_sku", {}).items():
                    if _sku_key.startswith(cat_prefix) and _entry.get("category_data") is not None:
                        _ref_data = _entry.get("merged_data") or {}
                        if _ref_data:
                            reference_row = _ref_data
                            break

            for old_row in old_rows:
                old_sku_raw = str(old_row.get("seller-sku") or old_row.get("sku") or "").strip().upper()
                if not old_sku_raw:
                    continue
                try:
                    old_parsed = parse_sku(old_sku_raw)
                except ValueError:
                    no_price_skus.append(old_sku_raw)
                    continue

                old_price_raw = old_row.get("price") or old_row.get("standard_price")
                try:
                    new_price, list_price = calculate_prices(old_price_raw)
                except ValueError:
                    no_price_skus.append(old_sku_raw)
                    continue

                new_sku = build_new_sku(old_parsed, old_pc, new_pc, suffix)

                # 先用参考行填底，再用本行覆盖（保留本行特有字段如 seller-sku、asin1、price、size）
                if reference_row is not None and reference_row is not old_row:
                    row = {**reference_row, **old_row}
                else:
                    row = dict(old_row)
                row["item_sku"] = new_sku
                fr_asin = fr_asin_map.get(old_sku_raw.upper()) if fr_asin_map else None
                row["external_product_id"] = fr_asin or old_row.get("asin1") or old_row.get("product-id") or ""
                row["external_product_id_type"] = "ASIN"
                row["model"] = new_sku
                row["part_number"] = new_sku
                row["standard_price"] = new_price
                row["list_price"] = list_price
                row["quantity"] = 2
                for img_col in IMAGE_COLUMNS:
                    row[img_col] = ""

                all_rows.append(row)

            _progress(40 + int(50 * (idx + 1) / max(total_groups, 1)))

        # 5. 写入模板
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_name = f"{request.country.value}-跟卖上新-{timestamp}.xlsx"
        output_path = RESULTS_DIR / output_name
        template_path = _resolve_template_path(profile.template_file)
        _write_to_template(template_path, output_path, all_rows)

        _progress(100)

        return FollowSellResult(
            output_file=output_name,
            processed_count=len(all_rows),
            skipped_skus=skipped_skus,
            invalid_skus=invalid_skus,
            no_price_skus=no_price_skus,
            identity_skus=identity_skus,
        )
