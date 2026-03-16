# backend/tests/test_follow_sell_processor.py
"""跟卖处理器单元测试。"""
import pytest
from pathlib import Path
from app.core.processors.follow_sell_processor import load_product_mapping


def test_load_mapping_reads_real_file():
    """映射文件存在时可以正确加载。"""
    mapping_path = Path(__file__).parent.parent / "uploads" / "新老款映射信息(1).xlsx"
    if not mapping_path.exists():
        pytest.skip("映射文件不存在，跳过")
    mapping = load_product_mapping(mapping_path)
    # EG02088 -> EG02084 应该在映射里
    assert mapping.get("EG02088") == "EG02084"


def test_load_mapping_skips_blank_rows(tmp_path):
    """空行和 None 值应跳过，不报错。"""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["老款号", "新款号", None])
    ws.append(["OLD001", "NEW001", None])
    ws.append([None, None, None])   # 空行
    ws.append(["", "NEW002", None])  # 老款为空
    p = tmp_path / "mapping.xlsx"
    wb.save(p)
    mapping = load_product_mapping(p)
    assert mapping == {"NEW001": "OLD001"}


def test_load_mapping_self_referential_row(tmp_path):
    """old_code == new_code 的行仍然加载进映射（由 processor 负责 warning）。"""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["老款号", "新款号"])
    ws.append(["ES02522", "ES02522"])
    p = tmp_path / "mapping.xlsx"
    wb.save(p)
    mapping = load_product_mapping(p)
    assert mapping.get("ES02522") == "ES02522"
