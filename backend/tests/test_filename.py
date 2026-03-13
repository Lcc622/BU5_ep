"""测试输出文件名生成逻辑。"""
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
from app.api import excel
from app.config import Country


def _make_request(country, prefixes, colors, mode):
    req = MagicMock()
    req.country = country
    req.selected_prefixes = prefixes
    req.target_colors = colors
    req.mode = mode
    return req


@patch("app.core.processors.add_color_size_processor.color_mapper")
def test_single_prefix_add_color(mock_mapper):
    from app.core.processors.add_color_size_processor import AddColorSizeProcessor
    proc = AddColorSizeProcessor()
    req = _make_request(Country.UK, ["EWJ19248"], ["BK", "RD"], "add-color")
    name = proc._resolve_output_filename(None, req)
    assert name == "UK-EWJ19248-补色 BK RD.xlsx"


@patch("app.core.processors.add_color_size_processor.color_mapper")
def test_two_prefixes_add_color(mock_mapper):
    from app.core.processors.add_color_size_processor import AddColorSizeProcessor
    proc = AddColorSizeProcessor()
    req = _make_request(Country.UK, ["EWJ19248", "EWJ20001"], ["BK"], "add-color")
    name = proc._resolve_output_filename(None, req)
    assert name == "UK-EWJ19248+EWJ20001-补色 BK.xlsx"


@patch("app.core.processors.add_color_size_processor.color_mapper")
def test_three_prefixes_add_color(mock_mapper):
    from app.core.processors.add_color_size_processor import AddColorSizeProcessor
    proc = AddColorSizeProcessor()
    req = _make_request(Country.UK, ["EWJ19248", "EWJ20001", "EWJ21000"], ["BK", "WH"], "add-color")
    name = proc._resolve_output_filename(None, req)
    assert name == "UK-3STYLE-补色 BK WH.xlsx"


@patch("app.core.processors.add_color_size_processor.color_mapper")
def test_single_prefix_add_code(mock_mapper):
    from app.core.processors.add_color_size_processor import AddColorSizeProcessor
    proc = AddColorSizeProcessor()
    req = _make_request(Country.FR, ["EWJ19248"], ["BK"], "add-code")
    name = proc._resolve_output_filename(None, req)
    assert name == "FR-EWJ19248-补码.xlsx"


@patch("app.core.processors.add_color_size_processor.color_mapper")
def test_custom_filename_unchanged(mock_mapper):
    from app.core.processors.add_color_size_processor import AddColorSizeProcessor
    proc = AddColorSizeProcessor()
    req = _make_request(Country.UK, ["EWJ19248"], ["BK"], "add-color")
    name = proc._resolve_output_filename("my_custom_output", req)
    assert name == "my_custom_output.xlsx"


def test_extract_original_upload_name():
    path = Path("UK_category_20260312053331_report_a.xlsx")
    assert excel._extract_original_upload_name(path, Country.UK, "category") == "report_a.xlsx"


def test_cleanup_old_uploads_removes_all_previous_all_listings(monkeypatch, tmp_path):
    monkeypatch.setattr(excel, "UPLOADS_DIR", tmp_path)
    keep_path = tmp_path / "UK_all_listings_20260312053331_latest.txt"
    old_path = tmp_path / "UK_all_listings_20260311053331_old.txt"
    keep_path.write_text("latest", encoding="utf-8")
    old_path.write_text("old", encoding="utf-8")

    excel._cleanup_old_uploads(Country.UK, "all_listings", keep_path)

    assert keep_path.exists()
    assert not old_path.exists()


def test_cleanup_old_uploads_only_replaces_same_category_filename(monkeypatch, tmp_path):
    monkeypatch.setattr(excel, "UPLOADS_DIR", tmp_path)
    keep_path = tmp_path / "UK_category_20260312053331_report_a.xlsx"
    old_same_name = tmp_path / "UK_category_20260311053331_report_a.xlsx"
    other_report = tmp_path / "UK_category_20260311053331_report_b.xlsx"
    keep_path.write_text("latest", encoding="utf-8")
    old_same_name.write_text("old", encoding="utf-8")
    other_report.write_text("other", encoding="utf-8")

    excel._cleanup_old_uploads(
        Country.UK,
        "category",
        keep_path,
        keep_latest_only=False,
    )

    assert keep_path.exists()
    assert not old_same_name.exists()
    assert other_report.exists()
