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
    """获取所有颜色映射。"""
    try:
        return ColorMappingResponse(success=True, data=color_mapper.get_all_mappings())
    except Exception as exc:  # pragma: no cover - defensive API wrapper
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/search", response_model=ColorMappingSearchResponse)
async def search_mappings(keyword: str) -> ColorMappingSearchResponse:
    """按颜色代码或名称搜索。"""
    try:
        matches = color_mapper.search_mappings(keyword)
        return ColorMappingSearchResponse(success=True, data=matches, count=len(matches))
    except Exception as exc:  # pragma: no cover - defensive API wrapper
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("", response_model=ColorMappingResponse)
async def add_mapping(payload: ColorMapping | ColorMappingBatch) -> ColorMappingResponse:
    """添加或更新颜色映射，支持单个或批量模型。"""
    try:
        if isinstance(payload, ColorMapping):
            color_mapper.add_mapping(payload.code, payload.names)
        elif isinstance(payload, ColorMappingBatch):
            color_mapper.add_mappings_batch({item.code: item.names for item in payload.mappings})
        return ColorMappingResponse(success=True, message="颜色映射已保存")
    except Exception as exc:  # pragma: no cover - defensive API wrapper
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{code}", response_model=ColorMappingResponse)
async def delete_mapping(code: str) -> ColorMappingResponse:
    """删除指定颜色代码。"""
    try:
        deleted = color_mapper.delete_mapping(code)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"颜色代码 {code} 不存在")
        return ColorMappingResponse(success=True, message=f"颜色映射 {code} 已删除")
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive API wrapper
        raise HTTPException(status_code=500, detail=str(exc)) from exc
