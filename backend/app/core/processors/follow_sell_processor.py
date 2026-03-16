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
