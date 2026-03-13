"""Pydantic 数据模型 - Excel 上传与处理流程。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.config import Country as CountryEnum
from app.config import COUNTRY_PROFILES


class SKUInfo(BaseModel):
    """SKU 信息模型。"""

    raw_sku: str
    product_code: str
    color_code: str
    size_code: str
    suffix: str


class ColorDistribution(BaseModel):
    """颜色分布模型。"""

    color_code: str
    color_name: str | None = None
    count: int


class AnalysisResult(BaseModel):
    """All listings 文件分析结果。"""

    success: bool
    filename: str
    total_skus: int
    prefixes: list[str]
    suffixes: list[str]
    color_distribution: list[ColorDistribution]
    unique_colors: int = 0
    unknown_colors: list[str] = Field(default_factory=list)


class ProcessRequest(BaseModel):
    """异步 Excel 处理请求。"""

    country: CountryEnum = Field(..., description="目标国家")
    all_listings_file: str = Field(..., min_length=1, description="已上传的 all listings 文件名")
    category_files: list[str] = Field(..., min_length=1, description="已上传的 category 文件名列表")
    selected_prefixes: list[str] = Field(..., min_length=1, description="需要处理的 SKU 前缀")
    target_colors: list[str] = Field(..., min_length=1, description="目标颜色列表")
    start_size: str = Field(..., min_length=1, description="起始尺码")
    end_size: str = Field(..., min_length=1, description="结束尺码")
    size_step: int = Field(..., ge=1, description="尺码步长")
    mode: Literal["add-color", "add-code"] = Field(..., description="处理模式")

    @field_validator("all_listings_file", "start_size", "end_size")
    @classmethod
    def strip_required_value(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value cannot be blank")
        return stripped

    @field_validator("category_files", "selected_prefixes", "target_colors")
    @classmethod
    def strip_list_values(cls, values: list[str]) -> list[str]:
        normalized = [item.strip() for item in values if str(item).strip()]
        if not normalized:
            raise ValueError("list cannot be empty")
        return normalized

    @model_validator(mode="after")
    def validate_category_file_count(self) -> "ProcessRequest":
        expected = COUNTRY_PROFILES[self.country].required_category_reports
        if len(self.category_files) != expected:
            raise ValueError(
                f"{self.country.value} requires {expected} category file(s), "
                f"got {len(self.category_files)}."
            )
        return self


class UploadResponse(BaseModel):
    """基础上传响应。"""

    success: bool
    filename: str


class UploadedFilesResponse(BaseModel):
    """已上传文件列表。"""

    all_listings: list[str]
    category_listings: list[str]


class ProcessStartResponse(BaseModel):
    """异步任务创建响应。"""

    job_id: str
    status: Literal["pending"]


class ProcessResult(BaseModel):
    """处理完成后的结果信息。"""

    output_file: str
    processed_count: int
    skipped_count: int = 0


class JobStatusResponse(BaseModel):
    """异步任务状态响应。"""

    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    progress: int = Field(..., ge=0, le=100)
    result: ProcessResult | None = None
    error: str | None = None


class ResultFileInfo(BaseModel):
    """结果文件信息。"""

    filename: str
    modified_at: datetime


class ResultsListResponse(BaseModel):
    """结果文件列表响应。"""

    files: list[ResultFileInfo]

