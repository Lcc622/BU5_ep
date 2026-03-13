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
