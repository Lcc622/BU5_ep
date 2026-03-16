"""颜色映射管理模块（多语言版）。"""

import json
from typing import Dict, Optional

from app.config import COLOR_MAPPING_FILE

SUPPORTED_LANGS = ("en", "fr", "de", "it", "es")


def _empty_multilang(en_name: str = "") -> dict[str, str]:
    """创建空的多语言字典，英文可预填。"""
    return {lang: (en_name if lang == "en" else "") for lang in SUPPORTED_LANGS}


def _normalize_names(value: str | dict[str, str]) -> dict[str, str]:
    """统一将旧格式和部分缺失字段的多语言格式转换为标准结构。"""
    if isinstance(value, str):
        return _empty_multilang(value)

    entry = _empty_multilang()
    entry.update(
        {
            lang: str(name)
            for lang, name in value.items()
            if lang in SUPPORTED_LANGS and isinstance(name, str)
        }
    )
    return entry


class ColorMapper:
    """颜色映射管理器（多语言）。"""

    def __init__(self) -> None:
        self.mappings: Dict[str, Dict[str, str]] = {}
        self.load_mappings()

    def load_mappings(self) -> None:
        if not COLOR_MAPPING_FILE.exists():
            self.mappings = {}
            self.save_mappings()
            return

        try:
            with COLOR_MAPPING_FILE.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
            self.mappings = {
                code.upper(): _normalize_names(value)
                for code, value in raw.items()
            }
        except Exception as exc:
            print(f"加载颜色映射失败: {exc}")
            self.mappings = {}

    def save_mappings(self) -> None:
        try:
            with COLOR_MAPPING_FILE.open("w", encoding="utf-8") as handle:
                json.dump(self.mappings, handle, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"保存颜色映射失败: {exc}")
            raise

    def get_mapping(self, code: str, lang: str = "en") -> Optional[str]:
        return self.get_color_name(code, lang=lang)

    def get_color_name(self, code: str, lang: str = "en") -> Optional[str]:
        """按语言获取颜色名称，缺失时退回英文。"""
        entry = self.mappings.get(code.upper())
        if entry is None:
            return None

        name = entry.get(lang, "")
        if not name:
            name = entry.get("en", "")
        return name or None

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
        self.mappings[code.upper()] = _normalize_names(names)
        self.save_mappings()

    def add_mappings_batch(self, mappings: Dict[str, Dict[str, str]]) -> None:
        for code, names in mappings.items():
            self.mappings[code.upper()] = _normalize_names(names)
        self.save_mappings()

    def delete_mapping(self, code: str) -> bool:
        normalized = code.upper()
        if normalized not in self.mappings:
            return False

        del self.mappings[normalized]
        self.save_mappings()
        return True

    def set_mapping(self, code: str, names: Dict[str, str]) -> None:
        self.add_mapping(code, names)


color_mapper = ColorMapper()
