# backend/app/models/follow_sell.py
"""Pydantic 模型 - 跟卖上新流程。"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, field_validator
from app.config import Country as CountryEnum


class FollowSellRequest(BaseModel):
    """跟卖处理请求。"""
    country: CountryEnum = Field(..., description="目标国家（UK / FR / DE / IT / ES）")
    all_listings_files: list[str] = Field(..., min_length=1, description="已上传的 All Listings 文件名列表")
    fr_all_listings_file: str | None = Field(
        None,
        description="法国 All Listings 文件名（DE/IT/ES 跟卖必填，用于获取 FR ASIN）",
    )
    category_files: list[str] = Field(..., min_length=1, description="已上传的 Category Listings 文件名列表")
    new_skus: list[str] = Field(..., min_length=1, description="新款 SKU 列表（每行一个）")

    @field_validator("all_listings_files", "category_files", "new_skus", mode="before")
    @classmethod
    def strip_and_filter(cls, values: list[str]) -> list[str]:
        normalized = [v.strip() for v in values if str(v).strip()]
        if not normalized:
            raise ValueError("list cannot be empty")
        return normalized

    @field_validator("fr_all_listings_file")
    @classmethod
    def strip_optional_filename(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            raise ValueError("文件名不能为空")
        return stripped

class FollowSellResult(BaseModel):
    """跟卖处理结果。"""
    output_file: str
    processed_count: int = 0
    skipped_skus: list[str] = Field(default_factory=list)   # 映射找不到 / 老款无命中
    invalid_skus: list[str] = Field(default_factory=list)   # SKU 格式不合法
    no_price_skus: list[str] = Field(default_factory=list)  # 老款价格缺失，已跳过
    identity_skus: list[str] = Field(default_factory=list)  # old_code == new_code 疑似异常


class FollowSellJobStatus(BaseModel):
    """异步任务状态。"""
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    progress: int = Field(..., ge=0, le=100)
    result: FollowSellResult | None = None
    error: str | None = None
