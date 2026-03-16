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


from app.core.processors.follow_sell_processor import (
    scan_old_skus_by_prefix,
    build_new_sku,
)


def _make_index_entry(sku: str, asin: str, price: str) -> dict:
    """创建与 ListingIndexer.build_index 一致的 by_sku 条目结构。"""
    flat = {"seller-sku": sku, "asin1": asin, "price": price}
    return {"sku": sku, "prefix": None, "parsed_sku": None,
            "all_listings_data": flat, "category_data": None, "merged_data": flat}


def test_scan_old_skus_finds_all_sizes():
    """前缀扫描返回该颜色下所有尺码的老款 SKU 行（merged_data 平铺字典）。"""
    index = {
        "by_sku": {
            "EG02084BK04": _make_index_entry("EG02084BK04", "B0CRHFY886", "59.99"),
            "EG02084BK06": _make_index_entry("EG02084BK06", "B0CRHFPWGS", "59.99"),
            "EG02084BK08": _make_index_entry("EG02084BK08", "B0CRHFFCJB", "59.99"),
            "EG02084RD04": _make_index_entry("EG02084RD04", "B0OTHER1234", "59.99"),
        }
    }
    results = scan_old_skus_by_prefix(index, old_product_code="EG02084", color_code="BK")
    assert len(results) == 3
    skus = [r["seller-sku"] for r in results]
    assert "EG02084BK04" in skus
    assert "EG02084BK06" in skus
    assert "EG02084BK08" in skus
    assert "EG02084RD04" not in skus


def test_scan_old_skus_no_match():
    """前缀扫描无命中时返回空列表。"""
    index = {"by_sku": {"EG02084BK04": _make_index_entry("EG02084BK04", "B0X", "59.99")}}
    results = scan_old_skus_by_prefix(index, old_product_code="EG02084", color_code="LV")
    assert results == []


def test_build_new_sku_replaces_product_code():
    """新 SKU 由 new_product_code + 老款颜色 + 老款尺码 + suffix 拼接。"""
    assert build_new_sku("EG02084BK04", "EG02084", "EG02088", "-UK1") == "EG02088BK04-UK1"
    assert build_new_sku("EG02084BK06", "EG02084", "EG02088", "-UK1") == "EG02088BK06-UK1"


def test_build_new_sku_8char_product_code():
    """8 位产品码也能正确替换。"""
    assert build_new_sku("EP007518BK04", "EP007518", "EE007568", "-UK1") == "EE007568BK04-UK1"


from app.core.processors.follow_sell_processor import calculate_prices


def test_calculate_prices_standard():
    new_price, list_price = calculate_prices(59.99)
    assert new_price == 60.09
    assert list_price == 70.09


def test_calculate_prices_rounding():
    """确保两位小数精度。"""
    new_price, list_price = calculate_prices(29.95)
    assert new_price == 30.05
    assert list_price == 40.05


def test_calculate_prices_none_raises():
    """价格缺失时抛出 ValueError。"""
    with pytest.raises(ValueError, match="price"):
        calculate_prices(None)
