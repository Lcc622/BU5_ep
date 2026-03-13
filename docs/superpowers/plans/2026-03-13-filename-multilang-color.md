# 输出文件名规范化 + 颜色映射多语言 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将输出文件名改为 `{国家}-{STYLE}-{补色 BK RD / 补码}.xlsx` 格式，并将颜色映射从单语言（英文）升级为多语言（en/fr/de/it/es）结构。

**Architecture:**
- Task 1 独立：只改 processor 的文件名生成逻辑，不动其他模块。
- Task 2 改 colorMapping.json 数据结构 + 所有读写路径（color_mapper → processor → API → 前端），通过迁移脚本完成存量数据升级。

**Tech Stack:** Python 3.11 / FastAPI / Pydantic / openpyxl / React 18 + TypeScript

---

## Chunk 1: 输出文件名格式

### Task 1: 更新 `_resolve_output_filename`

**Files:**
- Modify: `backend/app/core/processors/add_color_size_processor.py:849-857`
- Test: `backend/tests/test_filename.py` (new)

规则：
- 格式：`{COUNTRY}-{STYLE_PART}-{OP_TYPE}{COLOR_PART}.xlsx`
- `STYLE_PART`：
  - 1 个 prefix → 直接使用，如 `EWJ19248`
  - 2 个 prefix → `+` 连接，如 `EWJ19248+EWJ20001`
  - 3 个及以上 → `{N}STYLE`，如 `3STYLE`
- `OP_TYPE`：`mode == "add-color"` → `补色`；`mode == "add-code"` → `补码`
- `COLOR_PART`：`mode == "add-color"` → ` BK RD BL`（空格开头，颜色码空格分隔）；`mode == "add-code"` → 空字符串

示例：
- `UK-EWJ19248-补色 BK RD.xlsx`
- `UK-EWJ19248+EWJ20001-补色 BK.xlsx`
- `UK-3STYLE-补码.xlsx`

- [ ] **Step 1.1: 写失败测试**

新建 `backend/tests/test_filename.py`：

```python
"""测试输出文件名生成逻辑。"""
import pytest
from unittest.mock import MagicMock, patch
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
    req = _make_request(Country.FR, ["EWJ19248"], [], "add-code")
    name = proc._resolve_output_filename(None, req)
    assert name == "FR-EWJ19248-补码.xlsx"


@patch("app.core.processors.add_color_size_processor.color_mapper")
def test_custom_filename_unchanged(mock_mapper):
    from app.core.processors.add_color_size_processor import AddColorSizeProcessor
    proc = AddColorSizeProcessor()
    req = _make_request(Country.UK, ["EWJ19248"], ["BK"], "add-color")
    name = proc._resolve_output_filename("my_custom_output", req)
    assert name == "my_custom_output.xlsx"
```

- [ ] **Step 1.2: 运行测试确认失败**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep/backend
python -m pytest tests/test_filename.py -v
```
Expected: FAIL（`_resolve_output_filename` 签名不匹配）

- [ ] **Step 1.3: 修改 `_resolve_output_filename` 方法**

在 `add_color_size_processor.py` 中将方法签名和实现替换为：

```python
def _resolve_output_filename(self, output_filename: str | None, request: "ProcessRequest") -> str:
    if output_filename:
        filename = Path(output_filename).name
        if not filename.lower().endswith(".xlsx"):
            filename = f"{filename}.xlsx"
        return filename

    country = request.country.value  # "UK" / "FR" / ...
    prefixes = request.selected_prefixes
    mode = request.mode

    # STYLE_PART
    if len(prefixes) == 1:
        style_part = prefixes[0]
    elif len(prefixes) == 2:
        style_part = f"{prefixes[0]}+{prefixes[1]}"
    else:
        style_part = f"{len(prefixes)}STYLE"

    # OP_TYPE + COLOR_PART
    if mode == "add-color":
        color_part = " " + " ".join(request.target_colors) if request.target_colors else ""
        op_type = f"补色{color_part}"
    else:
        op_type = "补码"

    return f"{country}-{style_part}-{op_type}.xlsx"
```

- [ ] **Step 1.4: 找到方法的调用点，更新调用参数**

在 `add_color_size_processor.py` 中搜索 `_resolve_output_filename`，将所有调用从：

```python
output_name = self._resolve_output_filename(request.output_filename, request.country.value)
```

改为：

```python
output_name = self._resolve_output_filename(
    getattr(request, "output_filename", None), request
)
```

> 注意：`ProcessRequest` 目前没有 `output_filename` 字段，`getattr(..., None)` 确保向后兼容。

- [ ] **Step 1.5: 运行测试确认通过**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep/backend
python -m pytest tests/test_filename.py -v
```
Expected: 5 tests PASS

- [ ] **Step 1.6: 运行全量测试确认无回归**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep/backend
python -m pytest -v
```

- [ ] **Step 1.7: Commit**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep
git add backend/app/core/processors/add_color_size_processor.py backend/tests/test_filename.py
git commit -m "feat: 输出文件名改为 {国家}-{STYLE}-{补色/补码} 格式"
```

---

## Chunk 2: 颜色映射多语言支持

### Task 2: 迁移 colorMapping.json 数据结构

**Files:**
- Modify: `backend/data/colorMapping.json`
- New: `backend/scripts/migrate_color_mapping.py`

新结构（每个颜色码对应一个包含 5 种语言的字典）：

```json
{
  "BK": {
    "en": "Black",
    "fr": "Noir",
    "de": "Schwarz",
    "it": "Nero",
    "es": "Negro"
  }
}
```

- [ ] **Step 2.1: 创建迁移脚本** `backend/scripts/migrate_color_mapping.py`

```python
"""将 colorMapping.json 从单语言格式迁移到多语言格式。"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
COLOR_MAPPING_FILE = DATA_DIR / "colorMapping.json"

# 常用颜色的多语言翻译表（50个常用色）
TRANSLATIONS: dict[str, dict[str, str]] = {
    "BK": {"fr": "Noir", "de": "Schwarz", "it": "Nero", "es": "Negro"},
    "PK": {"fr": "Rose", "de": "Rosa", "it": "Rosa", "es": "Rosa"},
    "BH": {"fr": "Rose Blush", "de": "Blush", "it": "Rosa Cipria", "es": "Rosa Empolvado"},
    "HP": {"fr": "Rose Vif", "de": "Pink", "it": "Rosa Acceso", "es": "Rosa Fuerte"},
    "CO": {"fr": "Corail", "de": "Koralle", "it": "Corallo", "es": "Coral"},
    "RD": {"fr": "Rouge", "de": "Rot", "it": "Rosso", "es": "Rojo"},
    "BD": {"fr": "Bordeaux", "de": "Burgunder", "it": "Bordeaux", "es": "Burdeos"},
    "IB": {"fr": "Bleu Glace", "de": "Eisblau", "it": "Azzurro Ghiaccio", "es": "Azul Hielo"},
    "BL": {"fr": "Bleu Ciel", "de": "Himmelblau", "it": "Azzurro", "es": "Azul Cielo"},
    "AQ": {"fr": "Aqua", "de": "Aqua", "it": "Acqua", "es": "Agua"},
    "SB": {"fr": "Bleu Saphir", "de": "Saphirblau", "it": "Blu Zaffiro", "es": "Azul Zafiro"},
    "NB": {"fr": "Bleu Marine", "de": "Marineblau", "it": "Blu Navy", "es": "Azul Marino"},
    "IN": {"fr": "Indigo", "de": "Indigo", "it": "Indaco", "es": "Índigo"},
    "MN": {"fr": "Marine Nuit", "de": "Mitternachtsblau", "it": "Blu Notte", "es": "Azul Medianoche"},
    "MG": {"fr": "Vert Menthe", "de": "Mintgrün", "it": "Verde Menta", "es": "Verde Menta"},
    "EM": {"fr": "Vert Émeraude", "de": "Smaragdgrün", "it": "Verde Smeraldo", "es": "Verde Esmeralda"},
    "DG": {"fr": "Vert Foncé", "de": "Dunkelgrün", "it": "Verde Scuro", "es": "Verde Oscuro"},
    "TQ": {"fr": "Turquoise", "de": "Türkis", "it": "Turchese", "es": "Turquesa"},
    "GR": {"fr": "Vert", "de": "Grün", "it": "Verde", "es": "Verde"},
    "LV": {"fr": "Lavande", "de": "Lavendel", "it": "Lavanda", "es": "Lavanda"},
    "PW": {"fr": "Bleu Pervenche", "de": "Blauviolett", "it": "Pervinca", "es": "Azul Pervinca"},
    "DP": {"fr": "Violet Foncé", "de": "Dunkelviolett", "it": "Viola Scuro", "es": "Morado Oscuro"},
    "PP": {"fr": "Violet", "de": "Lila", "it": "Viola", "es": "Morado"},
    "YL": {"fr": "Jaune", "de": "Gelb", "it": "Giallo", "es": "Amarillo"},
    "WH": {"fr": "Blanc", "de": "Weiß", "it": "Bianco", "es": "Blanco"},
    "CR": {"fr": "Crème", "de": "Creme", "it": "Crema", "es": "Crema"},
    "MR": {"fr": "Champignon", "de": "Pilzbraun", "it": "Fungo", "es": "Seta"},
    "GY": {"fr": "Gris", "de": "Grau", "it": "Grigio", "es": "Gris"},
    "MB": {"fr": "Bleu Nuit", "de": "Mitternachtsblau", "it": "Blu Mezzanotte", "es": "Azul Medianoche"},
    "OR": {"fr": "Orange", "de": "Orange", "it": "Arancione", "es": "Naranja"},
    "BR": {"fr": "Marron", "de": "Braun", "it": "Marrone", "es": "Marrón"},
    "BG": {"fr": "Beige", "de": "Beige", "it": "Beige", "es": "Beige"},
    "CH": {"fr": "Charbon", "de": "Anthrazit", "it": "Antracite", "es": "Antracita"},
    "SL": {"fr": "Ardoise", "de": "Schiefer", "it": "Ardesia", "es": "Pizarra"},
    "TN": {"fr": "Bronzé", "de": "Gebräunt", "it": "Abbronzato", "es": "Tostado"},
    "OL": {"fr": "Olive", "de": "Olivgrün", "it": "Oliva", "es": "Oliva"},
    "RS": {"fr": "Rouille", "de": "Rost", "it": "Ruggine", "es": "Óxido"},
    "TL": {"fr": "Sarcelle", "de": "Blaugrün", "it": "Ottanio", "es": "Cerceta"},
    "PL": {"fr": "Prune", "de": "Pflaume", "it": "Prugna", "es": "Ciruela"},
    "MW": {"fr": "Blanc Cassé", "de": "Gebrochenes Weiß", "it": "Bianco Sporco", "es": "Blanco Roto"},
    "SK": {"fr": "Nude", "de": "Hautfarben", "it": "Nude", "es": "Nude"},
    "DW": {"fr": "Blanc Sale", "de": "Schmutzigweiß", "it": "Bianco Sporco", "es": "Blanco Sucio"},
    "LB": {"fr": "Bleu Clair", "de": "Hellblau", "it": "Azzurro Chiaro", "es": "Azul Claro"},
    "LP": {"fr": "Violet Clair", "de": "Hellviolett", "it": "Viola Chiaro", "es": "Lila Claro"},
    "LG": {"fr": "Vert Clair", "de": "Hellgrün", "it": "Verde Chiaro", "es": "Verde Claro"},
    "LY": {"fr": "Jaune Clair", "de": "Hellgelb", "it": "Giallo Chiaro", "es": "Amarillo Claro"},
    "LR": {"fr": "Rouge Clair", "de": "Hellrot", "it": "Rosso Chiaro", "es": "Rojo Claro"},
    "LN": {"fr": "Lin", "de": "Leinen", "it": "Lino", "es": "Lino"},
    "TW": {"fr": "Pied-de-Poule", "de": "Tweed", "it": "Tweed", "es": "Tweed"},
    "PT": {"fr": "Imprimé", "de": "Gemustert", "it": "Fantasia", "es": "Estampado"},
    "ST": {"fr": "Rayé", "de": "Gestreift", "it": "A Righe", "es": "A Rayas"},
}


def migrate():
    with COLOR_MAPPING_FILE.open("r", encoding="utf-8") as f:
        old: dict = json.load(f)

    # 已经是多语言格式则跳过
    first_val = next(iter(old.values()), None)
    if isinstance(first_val, dict):
        print("已经是多语言格式，无需迁移。")
        return

    new: dict[str, dict[str, str]] = {}
    for code, en_name in old.items():
        extra = TRANSLATIONS.get(code, {})
        new[code] = {
            "en": en_name,
            "fr": extra.get("fr", ""),
            "de": extra.get("de", ""),
            "it": extra.get("it", ""),
            "es": extra.get("es", ""),
        }

    # 备份原文件
    backup = COLOR_MAPPING_FILE.with_suffix(".json.bak")
    backup.write_bytes(COLOR_MAPPING_FILE.read_bytes())
    print(f"已备份原文件到 {backup}")

    with COLOR_MAPPING_FILE.open("w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False, indent=2)

    print(f"迁移完成，共 {len(new)} 个颜色码已转换为多语言格式。")


if __name__ == "__main__":
    migrate()
```

- [ ] **Step 2.2: 运行迁移**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep/backend
python scripts/migrate_color_mapping.py
```
Expected：输出"迁移完成，共 XX 个颜色码已转换为多语言格式。"

- [ ] **Step 2.3: Commit**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep
git add backend/scripts/migrate_color_mapping.py backend/data/colorMapping.json
git commit -m "feat: 迁移 colorMapping.json 至多语言结构 (en/fr/de/it/es)"
```

---

### Task 3: 更新 ColorMapper 支持多语言

**Files:**
- Modify: `backend/app/core/color_mapper.py`
- Test: `backend/tests/test_color_mapper.py` (new)

- [ ] **Step 3.1: 写失败测试** `backend/tests/test_color_mapper.py`

```python
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
```

- [ ] **Step 3.2: 运行测试确认失败**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep/backend
python -m pytest tests/test_color_mapper.py -v
```

- [ ] **Step 3.3: 重写 `color_mapper.py`**

```python
"""颜色映射管理模块（多语言版）。"""

import json
from typing import Dict, Optional

from app.config import COLOR_MAPPING_FILE

# 支持的语言列表
SUPPORTED_LANGS = ("en", "fr", "de", "it", "es")


def _empty_multilang(en_name: str = "") -> dict[str, str]:
    """创建空的多语言字典，英文可预填。"""
    return {lang: (en_name if lang == "en" else "") for lang in SUPPORTED_LANGS}


class ColorMapper:
    """颜色映射管理器（多语言）。"""

    def __init__(self) -> None:
        # mappings: { "BK": {"en": "Black", "fr": "Noir", ...} }
        self.mappings: Dict[str, Dict[str, str]] = {}
        self.load_mappings()

    def load_mappings(self) -> None:
        if COLOR_MAPPING_FILE.exists():
            try:
                with COLOR_MAPPING_FILE.open("r", encoding="utf-8") as handle:
                    raw = json.load(handle)
                # 兼容旧格式：{"BK": "Black"}
                for code, val in raw.items():
                    if isinstance(val, str):
                        self.mappings[code.upper()] = _empty_multilang(val)
                    else:
                        self.mappings[code.upper()] = val
            except Exception as exc:
                print(f"加载颜色映射失败: {exc}")
                self.mappings = {}
        else:
            self.mappings = {}
            self.save_mappings()

    def save_mappings(self) -> None:
        try:
            with COLOR_MAPPING_FILE.open("w", encoding="utf-8") as handle:
                json.dump(self.mappings, handle, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"保存颜色映射失败: {exc}")
            raise

    def get_all_mappings(self) -> Dict[str, Dict[str, str]]:
        return self.mappings.copy()

    def search_mappings(self, keyword: str) -> Dict[str, Dict[str, str]]:
        normalized = keyword.upper()
        return {
            code: names
            for code, names in self.mappings.items()
            if normalized in code.upper()
            or any(normalized in name.upper() for name in names.values() if name)
        }

    def add_mapping(self, code: str, names: Dict[str, str]) -> None:
        """添加或更新单个颜色映射（names 为多语言字典）。"""
        upper_code = code.upper()
        entry = _empty_multilang()
        entry.update({k: v for k, v in names.items() if k in SUPPORTED_LANGS})
        self.mappings[upper_code] = entry
        self.save_mappings()

    def add_mappings_batch(self, mappings: Dict[str, Dict[str, str]]) -> None:
        for code, names in mappings.items():
            entry = _empty_multilang()
            entry.update({k: v for k, v in names.items() if k in SUPPORTED_LANGS})
            self.mappings[code.upper()] = entry
        self.save_mappings()

    def delete_mapping(self, code: str) -> bool:
        normalized = code.upper()
        if normalized not in self.mappings:
            return False
        del self.mappings[normalized]
        self.save_mappings()
        return True

    def get_color_name(self, code: str, lang: str = "en") -> Optional[str]:
        """按语言获取颜色名称，缺失时 fallback 到英文。"""
        entry = self.mappings.get(code.upper())
        if entry is None:
            return None
        name = entry.get(lang, "")
        if not name:
            name = entry.get("en", "")
        return name or None

    def set_mapping(self, code: str, names: Dict[str, str]) -> None:
        self.add_mapping(code, names)

    def get_mapping(self, code: str, lang: str = "en") -> Optional[str]:
        return self.get_color_name(code, lang=lang)


color_mapper = ColorMapper()
```

- [ ] **Step 3.4: 运行测试确认通过**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep/backend
python -m pytest tests/test_color_mapper.py -v
```
Expected: 6 tests PASS

- [ ] **Step 3.5: Commit**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep
git add backend/app/core/color_mapper.py backend/tests/test_color_mapper.py
git commit -m "feat: ColorMapper 升级为多语言支持 (en/fr/de/it/es)"
```

---

### Task 4: 更新 Processor 调用颜色映射时传入语言

**Files:**
- Modify: `backend/app/core/processors/add_color_size_processor.py:836-837`

颜色名称查询需要根据国家的语言标签选择对应语言。

- [ ] **Step 4.1: 找到并更新 `_get_colour_name`**

当前代码（`add_color_size_processor.py` 第836行）：
```python
def _get_colour_name(self, color_code: str) -> str:
    return color_mapper.get_mapping(color_code) or color_code
```

改为：
```python
def _get_colour_name(self, color_code: str, lang: str = "en") -> str:
    return color_mapper.get_mapping(color_code, lang=lang) or color_code
```

- [ ] **Step 4.2: 在 `_build_output_row` 中提取语言码并传入**

当前（第441行）：
```python
new_colour = self._get_colour_name(new_color_code)
old_colour = self._get_source_colour_name(source_record)
```

改为：
```python
lang = profile.language_tag.split("_")[0]  # "en_GB" → "en"
new_colour = self._get_colour_name(new_color_code, lang=lang)
old_colour = self._get_source_colour_name(source_record, lang=lang)
```

- [ ] **Step 4.3: 更新 `_get_source_colour_name` 同样接受 `lang` 参数**

当前（第829-834行）：
```python
def _get_source_colour_name(self, record: _NormalizedRecord) -> str:
    source_colour = self._string_or_none(self._first_value(record.category_data, COLOUR_ALIASES))
    if source_colour:
        return source_colour
    if record.parsed_sku is not None:
        return self._get_colour_name(record.parsed_sku.color_code)
    return ""
```

改为：
```python
def _get_source_colour_name(self, record: _NormalizedRecord, lang: str = "en") -> str:
    source_colour = self._string_or_none(self._first_value(record.category_data, COLOUR_ALIASES))
    if source_colour:
        return source_colour
    if record.parsed_sku is not None:
        return self._get_colour_name(record.parsed_sku.color_code, lang=lang)
    return ""
```

- [ ] **Step 4.4: 运行全量测试**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep/backend
python -m pytest -v
```

- [ ] **Step 4.5: Commit**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep
git add backend/app/core/processors/add_color_size_processor.py
git commit -m "feat: 处理器按国家语言查询颜色名称"
```

---

### Task 5: 更新 Pydantic 模型与 API

**Files:**
- Modify: `backend/app/models/mapping.py`
- Modify: `backend/app/api/mapping.py`
- Modify: `backend/app/services/mapping_service.py`

颜色名称从 `str` 变为 `dict[str, str]`，API 请求/响应需同步更新。

- [ ] **Step 5.1: 更新 `backend/app/models/mapping.py`**

```python
"""Pydantic 数据模型 - 颜色映射（多语言版）。"""

from typing import Optional

from pydantic import BaseModel, Field


class ColorMapping(BaseModel):
    """颜色映射模型（多语言）。"""

    code: str = Field(..., description="颜色代码（2个大写字母）", min_length=2, max_length=2)
    names: dict[str, str] = Field(
        ...,
        description="各语言颜色名称，如 {'en': 'Black', 'fr': 'Noir', ...}",
    )


class ColorMappingBatch(BaseModel):
    """批量颜色映射模型。"""

    mappings: list[ColorMapping]


class ColorMappingResponse(BaseModel):
    """颜色映射响应模型。"""

    success: bool
    data: Optional[dict[str, dict[str, str]]] = None
    message: Optional[str] = None


class ColorMappingSearchResponse(BaseModel):
    """颜色映射搜索响应模型。"""

    success: bool
    data: Optional[dict[str, dict[str, str]]] = None
    count: int = 0
```

- [ ] **Step 5.2: 更新 `backend/app/services/mapping_service.py`**

```python
"""颜色映射服务。"""

from app.core.color_mapper import color_mapper


class MappingService:
    def get_all(self) -> dict[str, dict[str, str]]:
        return color_mapper.get_all_mappings()

    def upsert(self, code: str, names: dict[str, str]) -> None:
        color_mapper.set_mapping(code, names)

    def delete(self, code: str) -> bool:
        return color_mapper.delete_mapping(code)
```

- [ ] **Step 5.3: 更新 `backend/app/api/mapping.py`**

将 API 中所有 `payload.name` 改为 `payload.names`，以及字典值从 `str` 改为 `dict`：

```python
"""颜色映射 API 路由。"""

from fastapi import APIRouter, HTTPException

from app.core.color_mapper import color_mapper
from app.models.mapping import (
    ColorMapping,
    ColorMappingBatch,
    ColorMappingResponse,
    ColorMappingSearchResponse,
)

router = APIRouter(prefix="/api/mapping", tags=["mapping"])


@router.get("", response_model=ColorMappingResponse)
async def get_all_mappings() -> ColorMappingResponse:
    try:
        return ColorMappingResponse(success=True, data=color_mapper.get_all_mappings())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/search", response_model=ColorMappingSearchResponse)
async def search_mappings(keyword: str) -> ColorMappingSearchResponse:
    try:
        matches = color_mapper.search_mappings(keyword)
        return ColorMappingSearchResponse(success=True, data=matches, count=len(matches))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("", response_model=ColorMappingResponse)
async def add_mapping(payload: ColorMapping | ColorMappingBatch) -> ColorMappingResponse:
    try:
        if isinstance(payload, ColorMapping):
            color_mapper.add_mapping(payload.code, payload.names)
        elif isinstance(payload, ColorMappingBatch):
            color_mapper.add_mappings_batch({item.code: item.names for item in payload.mappings})
        return ColorMappingResponse(success=True, message="颜色映射已保存")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{code}", response_model=ColorMappingResponse)
async def delete_mapping(code: str) -> ColorMappingResponse:
    try:
        deleted = color_mapper.delete_mapping(code)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"颜色代码 {code} 不存在")
        return ColorMappingResponse(success=True, message=f"颜色映射 {code} 已删除")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
```

- [ ] **Step 5.4: 运行全量测试**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep/backend
python -m pytest -v
```

- [ ] **Step 5.5: 手动验证 API**

```bash
# 启动服务
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep/backend
uvicorn app.main:app --reload

# 另一个终端
curl http://localhost:8000/api/mapping | python -m json.tool | head -30
# 应看到: "BK": {"en": "Black", "fr": "Noir", ...}
```

- [ ] **Step 5.6: Commit**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep
git add backend/app/models/mapping.py backend/app/api/mapping.py backend/app/services/mapping_service.py
git commit -m "feat: 颜色映射 API 模型升级为多语言结构"
```

---

### Task 6: 更新前端颜色映射管理界面

**Files:**
- Modify: `frontend/src/components/ColorMapping/ColorMappingManager.tsx`

前端需要支持按语言编辑颜色名称：每行显示颜色码 + 5个语言输入框（en/fr/de/it/es），其中 en 为主展示字段。

- [ ] **Step 6.1: 阅读当前 `ColorMappingManager.tsx` 的完整内容**

```bash
cat /Users/melodylu/PycharmProjects/Bu2_ama_ep/frontend/src/components/ColorMapping/ColorMappingManager.tsx
```

- [ ] **Step 6.2: 更新类型定义**

在文件顶部的类型区域，将 `ColorEntry` 从：
```ts
interface ColorEntry {
  code: string;
  name: string;
}
```
改为：
```ts
const LANGS = ["en", "fr", "de", "it", "es"] as const;
type Lang = typeof LANGS[number];

interface ColorNames {
  en: string;
  fr: string;
  de: string;
  it: string;
  es: string;
}

interface ColorEntry {
  code: string;
  names: ColorNames;
}
```

- [ ] **Step 6.3: 更新数据获取与转换**

将原来解析 `data: Record<string, string>` 的地方改为 `data: Record<string, ColorNames>`，并在表格数据处理时使用 `names.en` 作为主显示名。

- [ ] **Step 6.4: 更新表格列**

在表格中：
- 主显示列：颜色名（英文）— `entry.names.en`
- 可展开/编辑状态下显示 5 个语言输入框（一行内并排或折叠）
- 编辑提交时发送 `{ code, names: { en, fr, de, it, es } }`

- [ ] **Step 6.5: 更新新增/编辑表单**

表单中将单个"颜色名称"输入框改为 5 个语言输入框（标签：EN / FR / DE / IT / ES），其中 EN 为必填。

- [ ] **Step 6.6: 前端构建验证**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep/frontend
npm run build
```
Expected: 无 TypeScript 错误，build 成功。

- [ ] **Step 6.7: Commit**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep
git add frontend/src/components/ColorMapping/ColorMappingManager.tsx
git commit -m "feat: 颜色映射管理界面支持多语言编辑"
```

---

## 完成检查

- [ ] 所有测试通过：`cd backend && python -m pytest -v`
- [ ] 前端构建成功：`cd frontend && npm run build`
- [ ] 输出文件名格式正确（手动确认）
- [ ] `colorMapping.json` 已为多语言结构（手动确认）
- [ ] API `/api/mapping` 返回多语言结构（curl 验证）
