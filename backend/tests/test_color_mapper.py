"""测试 ColorMapper 多语言支持。"""
import json
import pytest
from pathlib import Path


@pytest.fixture
def multilang_file(tmp_path):
    data = {
        "BK": {"en": "Black", "fr": "Noir", "de": "Schwarz", "it": "Nero", "es": "Negro"},
        "PK": {"en": "Pink", "fr": "Rose", "de": "Rosa", "it": "Rosa", "es": "Rosa"},
    }
    mapping_file = tmp_path / "colorMapping.json"
    mapping_file.write_text(json.dumps(data), encoding="utf-8")
    return mapping_file


def test_get_mapping_english(multilang_file, monkeypatch):
    import app.config as cfg
    monkeypatch.setattr(cfg, "COLOR_MAPPING_FILE", multilang_file)
    from importlib import reload
    import app.core.color_mapper as cm_module
    reload(cm_module)
    mapper = cm_module.ColorMapper()
    assert mapper.get_mapping("BK", lang="en") == "Black"


def test_get_mapping_french(multilang_file, monkeypatch):
    import app.config as cfg
    monkeypatch.setattr(cfg, "COLOR_MAPPING_FILE", multilang_file)
    from importlib import reload
    import app.core.color_mapper as cm_module
    reload(cm_module)
    mapper = cm_module.ColorMapper()
    assert mapper.get_mapping("BK", lang="fr") == "Noir"


def test_get_mapping_default_lang_is_english(multilang_file, monkeypatch):
    import app.config as cfg
    monkeypatch.setattr(cfg, "COLOR_MAPPING_FILE", multilang_file)
    from importlib import reload
    import app.core.color_mapper as cm_module
    reload(cm_module)
    mapper = cm_module.ColorMapper()
    assert mapper.get_mapping("BK") == "Black"


def test_get_mapping_missing_lang_falls_back_to_en(multilang_file, monkeypatch):
    """某语言空字符串时退回英文。"""
    data = {"BK": {"en": "Black", "fr": "", "de": "Schwarz", "it": "", "es": ""}}
    multilang_file.write_text(json.dumps(data), encoding="utf-8")
    import app.config as cfg
    monkeypatch.setattr(cfg, "COLOR_MAPPING_FILE", multilang_file)
    from importlib import reload
    import app.core.color_mapper as cm_module
    reload(cm_module)
    mapper = cm_module.ColorMapper()
    assert mapper.get_mapping("BK", lang="fr") == "Black"


def test_add_mapping_creates_multilang_entry(multilang_file, monkeypatch):
    import app.config as cfg
    monkeypatch.setattr(cfg, "COLOR_MAPPING_FILE", multilang_file)
    from importlib import reload
    import app.core.color_mapper as cm_module
    reload(cm_module)
    mapper = cm_module.ColorMapper()
    mapper.add_mapping("RD", {"en": "Red", "fr": "Rouge", "de": "Rot", "it": "Rosso", "es": "Rojo"})
    assert mapper.get_mapping("RD", lang="fr") == "Rouge"


def test_get_all_mappings_returns_multilang_dicts(multilang_file, monkeypatch):
    import app.config as cfg
    monkeypatch.setattr(cfg, "COLOR_MAPPING_FILE", multilang_file)
    from importlib import reload
    import app.core.color_mapper as cm_module
    reload(cm_module)
    mapper = cm_module.ColorMapper()
    all_m = mapper.get_all_mappings()
    assert isinstance(all_m["BK"], dict)
    assert "en" in all_m["BK"]


def test_legacy_format_loaded_correctly(tmp_path, monkeypatch):
    """旧格式 {"BK": "Black"} 加载时应自动转换为多语言格式。"""
    legacy_data = {"BK": "Black", "PK": "Pink"}
    mapping_file = tmp_path / "colorMapping.json"
    mapping_file.write_text(json.dumps(legacy_data), encoding="utf-8")
    import app.config as cfg
    monkeypatch.setattr(cfg, "COLOR_MAPPING_FILE", mapping_file)
    from importlib import reload
    import app.core.color_mapper as cm_module
    reload(cm_module)
    mapper = cm_module.ColorMapper()
    assert mapper.get_mapping("BK", lang="en") == "Black"
    assert mapper.get_mapping("BK", lang="fr") == "Black"  # fallback to en
