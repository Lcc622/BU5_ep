# backend/app/core/processors/follow_sell_processor.py
"""跟卖上新处理器。"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from openpyxl import load_workbook
from app.config import UPLOADS_DIR


MAPPING_FILENAME = "新老款映射信息(1).xlsx"


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
    """在 by_sku 索引中按前缀扫描老款 SKU 行，返回 merged_data 平铺字典列表。

    老款 SKU 在 All Listings 中无国家后缀（如 EG02084BK04）。
    不使用 parse_sku()，直接按字符串前缀匹配。

    by_sku 条目结构（来自 ListingIndexer.build_index）:
      { "sku": ..., "merged_data": {...flat fields...}, "all_listings_data": {...}, ... }
    返回 merged_data（平铺字段），不含嵌套子字典。
    """
    prefix = (old_product_code + color_code).upper()
    by_sku: dict[str, Any] = index.get("by_sku", {}) if isinstance(index, dict) else {}
    results = []
    for raw_sku, entry in by_sku.items():
        if not raw_sku.upper().startswith(prefix):
            continue
        if not isinstance(entry, dict):
            continue
        # 取平铺数据：merged_data 优先，fallback 到 all_listings_data
        flat = entry.get("merged_data") or entry.get("all_listings_data") or {}
        if flat:
            results.append(flat)
    return results


def build_new_sku(old_sku: str, old_product_code: str, new_product_code: str, suffix: str) -> str:
    """将老款 SKU 中的产品码替换为新款产品码，并拼接 suffix。

    old_sku 格式：product_code + color_code + size_code（无后缀）
    示例：EG02084BK04 + old=EG02084 + new=EG02088 + -UK1 → EG02088BK04-UK1
    """
    rest = old_sku.upper()[len(old_product_code):]   # 切掉老产品码，保留颜色+尺码
    return new_product_code.upper() + rest + suffix
