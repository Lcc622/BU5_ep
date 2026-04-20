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
    FollowSellProcessor,
    build_fr_asin_index,
    scan_old_skus_by_prefix,
    build_new_sku,
    normalize_sku_input,
)
from app.models.follow_sell import FollowSellRequest


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


def test_scan_includes_co_suffix_old_skus():
    """前缀扫描应保留带国家后缀的老款 SKU。"""
    index = {
        "by_sku": {
            "EG02084BK04-CO": _make_index_entry("EG02084BK04-CO", "B0CO123456", "59.99"),
            "EG02084BK06": _make_index_entry("EG02084BK06", "B0BASE12345", "59.99"),
        }
    }
    results = scan_old_skus_by_prefix(index, old_product_code="EG02084", color_code="BK")
    skus = [r["seller-sku"] for r in results]
    assert "EG02084BK04-CO" in skus
    assert "EG02084BK06" in skus


def test_build_fr_asin_index_prefers_asin1(monkeypatch, tmp_path):
    """FR All Listings 索引应提取 sku->asin，并优先使用 asin1。"""
    fr_file = tmp_path / "fr_all_listings.txt"
    fr_file.write_text("", encoding="utf-8")

    def fake_build_index(self, listings_files, category_files):
        assert listings_files == [fr_file]
        assert category_files == []
        return {
            "by_sku": {
                "EG02084BK04": {
                    "all_listings_data": {"seller-sku": "EG02084BK04", "asin1": "B0FRASIN1"},
                    "merged_data": {"seller-sku": "EG02084BK04", "asin1": "B0FRASIN1"},
                },
                "EG02084BK06": {
                    "all_listings_data": {"seller-sku": "EG02084BK06", "product-id": "B0FRPID06"},
                    "merged_data": {"seller-sku": "EG02084BK06", "product-id": "B0FRPID06"},
                },
                "EG02084BK08": {
                    "all_listings_data": {"seller-sku": "EG02084BK08"},
                    "merged_data": {"seller-sku": "EG02084BK08"},
                },
            }
        }

    monkeypatch.setattr("app.core.indexers.listing_indexer.ListingIndexer.build_index", fake_build_index)

    assert build_fr_asin_index(fr_file) == {
        "EG02084BK04": "B0FRASIN1",
        "EG02084BK06": "B0FRPID06",
    }


def test_build_new_sku_replaces_product_code():
    """新 SKU 由 new_product_code + 老款颜色 + 老款尺码 + suffix 拼接。"""
    old_info_a = parse_sku("EG02084BK04")
    old_info_b = parse_sku("EG02084BK06")
    assert build_new_sku(old_info_a, "EG02084", "EG02088", target_suffix="-UK1") == "EG02088BK04-UK1"
    assert build_new_sku(old_info_b, "EG02084", "EG02088", target_suffix="-UK1") == "EG02088BK06-UK1"


def test_build_new_sku_8char_product_code():
    """8 位产品码也能正确替换。"""
    old_info = parse_sku("EP007518BK04")
    assert build_new_sku(old_info, "EP007518", "EE007568", target_suffix="-UK1") == "EE007568BK04-UK1"


def test_build_new_sku_no_suffix():
    """目标 SKU 无后缀时不应追加任何后缀。"""
    old_info = parse_sku("EG02084BK04-CO")
    assert build_new_sku(old_info, "EG02084", "EG02088", target_suffix=None) == "EG02088BK04"


def test_build_new_sku_co_no_double_suffix():
    """老款已有 CO 后缀时，应仅使用目标后缀一次。"""
    old_info = parse_sku("EG02084BK04-CO")
    assert build_new_sku(old_info, "EG02084", "EG02088", target_suffix="-CO") == "EG02088BK04-CO"


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


from app.core.parsers.sku import parse_sku


def test_parse_sku_no_suffix():
    """无后缀 SKU 应返回 suffix=None。"""
    info = parse_sku("EG02088BK04")
    assert info.suffix is None
    assert info.product_code == "EG02088"
    assert info.color_code == "BK"
    assert info.size_code == "04"


def test_parse_sku_co_suffix():
    """两位国家后缀应被正确识别。"""
    info = parse_sku("EG02088BK04-CO")
    assert info.suffix == "-CO"
    assert info.product_code == "EG02088"
    assert info.color_code == "BK"
    assert info.size_code == "04"


def test_parse_sku_uk1_still_works():
    """UK1 后缀兼容旧逻辑。"""
    info = parse_sku("EG02088BK04-UK1")
    assert info.suffix == "-UK1"
    assert info.product_code == "EG02088"
    assert info.color_code == "BK"
    assert info.size_code == "04"


def test_normalize_uk_strips_plus():
    """UK 输入需要去掉末尾加号。"""
    from app.config import Country

    assert normalize_sku_input("  EG02088BK04-UK1+  ", Country.UK) == "EG02088BK04-UK1"


def test_normalize_fr_no_change():
    """非 UK 国家只做首尾空白清理。"""
    from app.config import Country

    assert normalize_sku_input("  EG02088BK04-CO+  ", Country.FR) == "EG02088BK04-CO+"


def test_uk1_plus_suffix_normalized():
    """-UK1+ 后缀应归一化为 -UK1 后能正常解析。"""
    from app.config import Country

    normalized = normalize_sku_input("EG02088BK04-UK1+", Country.UK)
    info = parse_sku(normalized)
    assert info.suffix == "-UK1"
    assert info.product_code == "EG02088"
    assert info.color_code == "BK"
    assert info.size_code == "04"


def test_process_prefers_fr_asin_for_de(monkeypatch, tmp_path):
    """DE/IT/ES 跟卖时，external_product_id 应优先使用 FR ASIN。"""
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "app.core.processors.follow_sell_processor.load_product_mapping",
        lambda mapping_path=None: {"EG02088": "EG02084"},
    )

    index = {
        "by_sku": {
            "EG02084BK04": {
                "merged_data": {
                    "seller-sku": "EG02084BK04",
                    "asin1": "B0DELOCAL04",
                    "price": "59.99",
                },
                "all_listings_data": {
                    "seller-sku": "EG02084BK04",
                    "asin1": "B0DELOCAL04",
                    "price": "59.99",
                },
                "category_data": None,
            }
        }
    }
    monkeypatch.setattr(
        "app.core.indexers.listing_indexer.ListingIndexer.build_index",
        lambda self, listings_file, category_files: index,
    )
    monkeypatch.setattr(
        "app.core.processors.follow_sell_processor.build_fr_asin_index",
        lambda path: {"EG02084BK04": "B0FRPRIORITY4"},
    )

    template_path = tmp_path / "template.xlsx"
    template_path.write_text("template", encoding="utf-8")
    monkeypatch.setattr(
        "app.core.processors.follow_sell_processor._resolve_template_path",
        lambda template_file: template_path,
    )

    def fake_write_to_template(template_path_arg, output_path_arg, rows):
        captured["template_path"] = template_path_arg
        captured["output_path"] = output_path_arg
        captured["rows"] = rows

    monkeypatch.setattr(
        "app.core.processors.follow_sell_processor._write_to_template",
        fake_write_to_template,
    )

    request = FollowSellRequest(
        country="DE",
        all_listings_files=["de_all.tsv"],
        fr_all_listings_file="fr_all.tsv",
        category_files=["de_category.xlsx", "de_category_2.xlsx"],
        new_skus=["EG02088BK04"],
    )

    result = FollowSellProcessor().process(request)

    assert result.processed_count == 1
    rows = captured["rows"]
    assert isinstance(rows, list)
    assert rows[0]["external_product_id"] == "B0FRPRIORITY4"
    assert rows[0]["item_sku"] == "EG02088BK04"
