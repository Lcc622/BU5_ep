# 跟卖上新 (Follow-Sell) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 UK 站跟卖上新功能——输入新款 SKU 批量生成跟卖上传模板，自动补全同色所有尺码，输出含 9 个必改字段的 Excel 文件。

**Architecture:** 新增独立的 `follow_sell_processor.py` 处理核心逻辑（映射加载 → All Listings 前缀扫描 → 字段生成 → 写模板），配套 FastAPI 路由 `/api/follow-sell` 复用现有异步任务架构，前端新增 `/follow-sell` 页面（3 步流程）。

**Tech Stack:** Python 3.11, FastAPI, openpyxl, Pydantic v2, React 18, TypeScript, Zustand, Axios, Tailwind CSS

**Spec:** `docs/superpowers/specs/2026-03-16-follow-sell-design.md`

---

## File Map

| 状态 | 路径 | 职责 |
|------|------|------|
| 新增 | `backend/app/models/follow_sell.py` | Pydantic 请求/响应模型 |
| 新增 | `backend/app/core/processors/follow_sell_processor.py` | 核心处理逻辑 |
| 新增 | `backend/app/api/follow_sell.py` | FastAPI 路由 |
| 修改 | `backend/app/main.py` | 注册新路由 |
| 新增 | `backend/tests/test_follow_sell_processor.py` | 处理器单元测试 |
| 新增 | `frontend/src/services/followSellApi.ts` | API 调用层 |
| 新增 | `frontend/src/pages/FollowSell.tsx` | 跟卖页面（3步流程） |
| 修改 | `frontend/src/App.tsx` | 添加路由 + 导航入口 |

---

## Chunk 1: 后端模型与处理器核心

### Task 1: Pydantic 模型

**Files:**
- Create: `backend/app/models/follow_sell.py`

- [ ] **Step 1: 创建模型文件**

```python
# backend/app/models/follow_sell.py
"""Pydantic 模型 - 跟卖上新流程。"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, field_validator
from app.config import Country as CountryEnum, COUNTRY_PROFILES


class FollowSellRequest(BaseModel):
    """跟卖处理请求。"""
    country: CountryEnum = Field(..., description="目标国家（当前仅 UK）")
    all_listings_file: str = Field(..., min_length=1, description="已上传的 All Listings 文件名")
    category_files: list[str] = Field(..., min_length=1, description="已上传的 Category Listings 文件名列表")
    new_skus: list[str] = Field(..., min_length=1, description="新款 SKU 列表（每行一个）")

    @field_validator("new_skus", mode="before")
    @classmethod
    def strip_and_filter(cls, values: list[str]) -> list[str]:
        normalized = [v.strip() for v in values if str(v).strip()]
        if not normalized:
            raise ValueError("new_skus 不能为空")
        return normalized

    @field_validator("all_listings_file")
    @classmethod
    def strip_filename(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("文件名不能为空")
        return stripped

    def validate_category_count(self) -> None:
        expected = COUNTRY_PROFILES[self.country].required_category_reports
        if len(self.category_files) != expected:
            raise ValueError(
                f"{self.country.value} 需要 {expected} 张 Category 文件，实际 {len(self.category_files)} 张"
            )


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
```

- [ ] **Step 2: 验证模型可导入**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep/backend
python3 -c "from app.models.follow_sell import FollowSellRequest, FollowSellResult, FollowSellJobStatus; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/follow_sell.py
git commit -m "feat(follow-sell): add Pydantic models"
```

---

### Task 2: 映射表加载器（含测试）

**Files:**
- Create: `backend/app/core/processors/follow_sell_processor.py`（仅 loader 部分）
- Create: `backend/tests/test_follow_sell_processor.py`

- [ ] **Step 1: 写失败测试**

```python
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
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep/backend
python3 -m pytest tests/test_follow_sell_processor.py -v 2>&1 | head -20
```

Expected: `ImportError` 或 `ModuleNotFoundError`（函数未实现）

- [ ] **Step 3: 实现 `load_product_mapping`**

```python
# backend/app/core/processors/follow_sell_processor.py
"""跟卖上新处理器。"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from openpyxl import load_workbook
from app.config import UPLOADS_DIR


MAPPING_FILENAME = "新老款映射信息(1).xlsx"


def load_product_mapping(mapping_path: Path | None = None) -> dict[str, str]:
    """加载新老款产品码对照表。

    Returns:
        {new_product_code: old_product_code}
    """
    path = mapping_path or (UPLOADS_DIR / MAPPING_FILENAME)
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    mapping: dict[str, str] = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        old_code = str(row[0] or "").strip().upper()
        new_code = str(row[1] or "").strip().upper()
        if old_code and new_code:
            mapping[new_code] = old_code
    wb.close()
    return mapping
```

- [ ] **Step 4: 运行确认通过**

```bash
python3 -m pytest tests/test_follow_sell_processor.py::test_load_mapping_reads_real_file tests/test_follow_sell_processor.py::test_load_mapping_skips_blank_rows tests/test_follow_sell_processor.py::test_load_mapping_self_referential_row -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/processors/follow_sell_processor.py backend/tests/test_follow_sell_processor.py
git commit -m "feat(follow-sell): add mapping loader with tests"
```

---

### Task 3: Old SKU 前缀扫描 + 新 SKU 生成（含测试）

**Files:**
- Modify: `backend/app/core/processors/follow_sell_processor.py`
- Modify: `backend/tests/test_follow_sell_processor.py`

- [ ] **Step 1: 追加测试**

在 `test_follow_sell_processor.py` 末尾添加：

```python
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
```

- [ ] **Step 2: 运行确认失败**

```bash
python3 -m pytest tests/test_follow_sell_processor.py -k "scan or build_new_sku" -v 2>&1 | head -20
```

Expected: `ImportError`

- [ ] **Step 3: 实现扫描和生成函数**

在 `follow_sell_processor.py` 中追加：

```python
def scan_old_skus_by_prefix(
    index: dict[str, Any],
    old_product_code: str,
    color_code: str,
) -> list[dict[str, Any]]:
    """在 by_sku 索引中按前缀扫描老款 SKU 行，返回 merged_data 平铺字典列表。

    老款 SKU 在 All Listings 中无国家后缀（如 EG02084BK04）。
    不使用 parse_sku()，直接按字符串前缀匹配。

    by_sku 条目结构（来自 ListingIndexer.build_index）:
      { "sku": ..., "merged_data": {...flat fields...}, "all_listings_data": {...}, ... }
    返回 merged_data（平铺字段），不含嵌套子字典。
    """
    prefix = (old_product_code + color_code).upper()
    by_sku: dict[str, Any] = index.get("by_sku", {}) if isinstance(index, dict) else {}
    results = []
    for raw_sku, entry in by_sku.items():
        if not raw_sku.upper().startswith(prefix):
            continue
        if not isinstance(entry, dict):
            continue
        # 取平铺数据：merged_data 优先，fallback 到 all_listings_data
        flat = entry.get("merged_data") or entry.get("all_listings_data") or {}
        if flat:
            results.append(flat)
    return results


def build_new_sku(old_sku: str, old_product_code: str, new_product_code: str, suffix: str) -> str:
    """将老款 SKU 中的产品码替换为新款产品码，并拼接 suffix。

    old_sku 格式：product_code + color_code + size_code（无后缀）
    示例：EG02084BK04 + old=EG02084 + new=EG02088 + -UK1 → EG02088BK04-UK1
    """
    rest = old_sku.upper()[len(old_product_code):]   # 切掉老产品码，保留颜色+尺码
    return new_product_code.upper() + rest + suffix
```

- [ ] **Step 4: 运行确认通过**

```bash
python3 -m pytest tests/test_follow_sell_processor.py -v
```

Expected: 全部 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/processors/follow_sell_processor.py backend/tests/test_follow_sell_processor.py
git commit -m "feat(follow-sell): add old-SKU prefix scan and new-SKU builder"
```

---

### Task 4: 价格计算 + 完整 process() 方法（含集成测试）

**Files:**
- Modify: `backend/app/core/processors/follow_sell_processor.py`
- Modify: `backend/tests/test_follow_sell_processor.py`

- [ ] **Step 1: 追加价格测试 + 集成测试**

```python
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
```

- [ ] **Step 2: 实现 `calculate_prices`**

```python
def calculate_prices(old_price: Any) -> tuple[float, float]:
    """计算新版本售价和 RRP。

    Raises:
        ValueError: 老款价格缺失或无法解析
    """
    if old_price is None or str(old_price).strip() == "":
        raise ValueError("老款 price 缺失，无法计算新价格")
    try:
        base = round(float(old_price), 2)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"老款 price 无法解析: {old_price!r}") from exc
    new_price = round(base + 0.1, 2)
    list_price = round(new_price + 10, 2)
    return new_price, list_price
```

- [ ] **Step 3: 实现完整的 `FollowSellProcessor.process()` 方法**

在 `follow_sell_processor.py` 中添加处理器类，包含 `process()` 主入口：

```python
import shutil
import threading
from datetime import datetime
from copy import copy
from typing import Any, Callable

from openpyxl import load_workbook

from app.config import (
    COUNTRY_PROFILES, RESULTS_DIR, TEMPLATES_DIR, UPLOADS_DIR, Country,
)
from app.core.indexers.listing_indexer import ListingIndexer
from app.core.parsers.sku import parse_sku
from app.models.follow_sell import FollowSellRequest, FollowSellResult


# 所有需要清空的图片列（机器列名）
IMAGE_COLUMNS = [
    "main_image_url",
    "other_image_url1", "other_image_url2", "other_image_url3",
    "other_image_url4", "other_image_url5", "other_image_url6",
    "other_image_url7", "other_image_url8",
]


class FollowSellProcessor:
    """跟卖上新处理器。"""

    def process(
        self,
        request: FollowSellRequest,
        progress_callback: Callable[[int], None] | None = None,
    ) -> FollowSellResult:
        def _progress(pct: int) -> None:
            if progress_callback:
                progress_callback(pct)

        _progress(5)

        # 1. 加载映射表
        mapping = load_product_mapping()
        if not mapping:
            raise RuntimeError("映射文件为空或不存在，请确认 backend/uploads/新老款映射信息(1).xlsx")

        _progress(10)

        # 2. 构建索引（All Listings + Category Listings）
        indexer = ListingIndexer()
        listings_path = UPLOADS_DIR / request.all_listings_file
        category_paths = [UPLOADS_DIR / f for f in request.category_files]
        index = indexer.build_index(listings_path, category_paths)

        _progress(30)

        # 3. 解析新款 SKU → 按 (new_product_code, color_code, suffix) 分组（suffix 取第一个）
        color_groups: dict[tuple[str, str], str] = {}  # (new_pc, color) -> suffix
        invalid_skus: list[str] = []
        for raw in request.new_skus:
            try:
                info = parse_sku(raw)
            except ValueError:
                invalid_skus.append(raw)
                continue
            key = (info.product_code, info.color_code)
            if key not in color_groups:
                color_groups[key] = info.suffix

        _progress(40)

        # 4. 对每个颜色组生成行
        profile = COUNTRY_PROFILES[request.country]
        all_rows: list[dict[str, Any]] = []
        skipped_skus: list[str] = []
        no_price_skus: list[str] = []
        identity_skus: list[str] = []

        total_groups = len(color_groups)
        for idx, ((new_pc, color_code), suffix) in enumerate(color_groups.items()):
            # 查映射
            old_pc = mapping.get(new_pc)
            if old_pc is None:
                skipped_skus.append(f"{new_pc}{color_code}{suffix}（映射表无此产品码）")
                continue
            if old_pc == new_pc:
                identity_skus.append(new_pc)

            # 前缀扫描
            old_rows = scan_old_skus_by_prefix(index, old_pc, color_code)
            if not old_rows:
                skipped_skus.append(f"{new_pc}{color_code}{suffix}（All Listings 无老款命中）")
                continue

            for old_row in old_rows:
                old_sku_raw = str(old_row.get("seller-sku") or old_row.get("sku") or "").strip().upper()
                if not old_sku_raw:
                    continue

                # 计算价格（缺失则跳过该行）
                old_price_raw = old_row.get("price") or old_row.get("standard_price")
                try:
                    new_price, list_price = calculate_prices(old_price_raw)
                except ValueError:
                    no_price_skus.append(old_sku_raw)
                    continue

                # 生成新 SKU
                new_sku = build_new_sku(old_sku_raw, old_pc, new_pc, suffix)

                # 构造输出行：先复制老款数据
                row: dict[str, Any] = dict(old_row)

                # 覆盖 9 个必改字段
                row["item_sku"] = new_sku
                row["external_product_id"] = old_row.get("asin1") or old_row.get("product-id") or ""
                row["external_product_id_type"] = "ASIN"
                row["model"] = new_sku
                row["part_number"] = new_sku
                row["standard_price"] = new_price
                row["list_price"] = list_price
                row["quantity"] = 2
                for img_col in IMAGE_COLUMNS:
                    row[img_col] = ""

                all_rows.append(row)

            _progress(40 + int(50 * (idx + 1) / max(total_groups, 1)))

        # 5. 写入模板
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_name = f"UK-跟卖上新-{timestamp}.xlsx"
        output_path = RESULTS_DIR / output_name
        template_path = _resolve_template_path(profile.template_file)
        _write_to_template(template_path, output_path, all_rows)

        _progress(100)

        return FollowSellResult(
            output_file=output_name,
            processed_count=len(all_rows),
            skipped_skus=skipped_skus,
            invalid_skus=invalid_skus,
            no_price_skus=no_price_skus,
            identity_skus=identity_skus,
        )


def _resolve_template_path(template_file: str) -> Path:
    """解析模板路径，兼容 Docker 和本地开发环境。

    Docker: ./templates 挂载到 /app/templates → TEMPLATES_DIR = /app/templates ✓
    本地:   templates/ 在项目根目录，TEMPLATES_DIR = backend/templates（不存在）
            → fallback 到项目根目录 templates/
    """
    docker_path = TEMPLATES_DIR / template_file
    if docker_path.exists():
        return docker_path
    # 本地 fallback：从当前文件向上 4 级到达项目根
    local_path = Path(__file__).resolve().parents[4] / "templates" / template_file
    if local_path.exists():
        return local_path
    raise FileNotFoundError(
        f"模板文件不存在: {template_file}\n"
        f"  尝试路径 1: {docker_path}\n"
        f"  尝试路径 2: {local_path}"
    )


def _write_to_template(
    template_path: Path,
    output_path: Path,
    rows: list[dict[str, Any]],
) -> None:
    """将行数据写入 Excel 模板（复用 UK AddColor 模板结构）。"""
    if not template_path.exists():
        raise FileNotFoundError(f"模板文件不存在: {template_path}")

    shutil.copy(template_path, output_path)
    wb = load_workbook(output_path)
    ws = wb.active

    # 读取模板表头（行 2 = 显示名，行 3 = 机器名）
    max_col = ws.max_column
    display_headers = {
        str(ws.cell(2, c).value or "").strip().casefold(): c
        for c in range(1, max_col + 1)
    }
    machine_headers = {
        str(ws.cell(3, c).value or "").strip().casefold(): c
        for c in range(1, max_col + 1)
    }

    def _col_idx(key: str) -> int | None:
        k = key.strip().casefold()
        return machine_headers.get(k) or display_headers.get(k)

    # 数据从第 5 行开始写（行 1~4 为表头区域）
    START_ROW = 5
    for row_idx, row_data in enumerate(rows, start=START_ROW):
        for field_key, value in row_data.items():
            col = _col_idx(field_key)
            if col is not None:
                ws.cell(row=row_idx, column=col, value=value)

    wb.save(output_path)
    wb.close()
```

- [ ] **Step 4: 运行所有测试**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep/backend
python3 -m pytest tests/test_follow_sell_processor.py -v
```

Expected: 全部 PASSED

- [ ] **Step 5: 冒烟测试（验证真实文件可跑通）**

```python
# 在 backend/ 目录下执行
python3 -c "
from app.core.processors.follow_sell_processor import FollowSellProcessor
from app.models.follow_sell import FollowSellRequest
from app.config import Country
req = FollowSellRequest(
    country=Country.UK,
    all_listings_file='UK_all_listings_20260313082242_All+Listings+Report_03-11-2026.txt',
    category_files=[
        'UK_category_20260313082255_0_APPAREL-DRESS.xlsm',
        'UK_category_20260313082258_1_DRESS.xlsm',
        'UK_category_20260313082301_2_PARTYDRESS.xlsm',
    ],
    new_skus=['EG02088BK04-UK1'],
)
result = FollowSellProcessor().process(req, progress_callback=lambda p: print(f'  {p}%'))
print('processed:', result.processed_count)
print('skipped:', result.skipped_skus)
print('no_price:', result.no_price_skus)
print('output:', result.output_file)
"
```

Expected: `processed: N`（N > 0），`output: UK-跟卖上新-*.xlsx`

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/processors/follow_sell_processor.py backend/tests/test_follow_sell_processor.py
git commit -m "feat(follow-sell): complete processor with price calc and template write"
```

---

## Chunk 2: 后端 API 路由

### Task 5: FastAPI 路由

**Files:**
- Create: `backend/app/api/follow_sell.py`

- [ ] **Step 1: 创建路由文件（参考 `excel.py` 的异步任务结构）**

```python
# backend/app/api/follow_sell.py
"""跟卖上新 API 路由。"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import RESULTS_DIR
from app.core.processors.follow_sell_processor import FollowSellProcessor
from app.models.follow_sell import (
    FollowSellJobStatus,
    FollowSellRequest,
    FollowSellResult,
)

router = APIRouter(prefix="/api/follow-sell", tags=["follow-sell"])

JOB_STATES: dict[str, dict[str, Any]] = {}
JOB_LOCK = threading.Lock()


def _result_filename(filename: str) -> str:
    name = Path(filename or "").name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    return name


@router.post("/process", response_model=FollowSellJobStatus)
async def start_follow_sell(request: FollowSellRequest) -> FollowSellJobStatus:
    """触发异步跟卖处理任务，返回 job_id。"""
    try:
        request.validate_category_count()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    job_id = str(uuid.uuid4())
    with JOB_LOCK:
        JOB_STATES[job_id] = {
            "status": "pending",
            "progress": 0,
            "result": None,
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def _run():
        with JOB_LOCK:
            JOB_STATES[job_id]["status"] = "running"

        def _progress(pct: int) -> None:
            with JOB_LOCK:
                JOB_STATES[job_id]["progress"] = pct

        try:
            result = FollowSellProcessor().process(request, progress_callback=_progress)
            with JOB_LOCK:
                JOB_STATES[job_id].update(
                    status="completed",
                    progress=100,
                    result=result.model_dump(),
                )
        except Exception as exc:  # noqa: BLE001
            with JOB_LOCK:
                JOB_STATES[job_id].update(status="failed", error=str(exc))

    threading.Thread(target=_run, daemon=True).start()
    return FollowSellJobStatus(job_id=job_id, status="pending", progress=0)


@router.get("/status/{job_id}", response_model=FollowSellJobStatus)
async def get_job_status(job_id: str) -> FollowSellJobStatus:
    """轮询任务状态。"""
    with JOB_LOCK:
        state = JOB_STATES.get(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {job_id}")

    result = None
    if state.get("result"):
        result = FollowSellResult(**state["result"])

    return FollowSellJobStatus(
        job_id=job_id,
        status=state["status"],
        progress=state["progress"],
        result=result,
        error=state.get("error"),
    )


@router.get("/download/{filename}")
async def download_result(filename: str) -> FileResponse:
    """下载结果文件。"""
    safe_name = _result_filename(filename)
    file_path = RESULTS_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"结果文件不存在: {safe_name}")
    return FileResponse(
        path=file_path,
        filename=safe_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
```

- [ ] **Step 2: 注册路由到 main.py**

在 `backend/app/main.py` 中找到现有 router 注册位置，添加：

```python
from app.api.follow_sell import router as follow_sell_router
# ...
app.include_router(follow_sell_router)
```

- [ ] **Step 3: 启动后验证路由可访问**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
sleep 2
curl -s http://localhost:8000/docs | grep -c "follow-sell" && echo "Routes OK"
kill %1
```

Expected: 输出 `1` 或更大数字，表示 route 已注册

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/follow_sell.py backend/app/main.py
git commit -m "feat(follow-sell): add FastAPI routes and register router"
```

---

## Chunk 3: 前端页面

### Task 6: API 服务层

**Files:**
- Create: `frontend/src/services/followSellApi.ts`

- [ ] **Step 1: 创建 API 服务**

```typescript
// frontend/src/services/followSellApi.ts
import axios from '../lib/axios';

export interface FollowSellRequest {
  country: string;
  all_listings_file: string;
  category_files: string[];
  new_skus: string[];
}

export interface FollowSellResult {
  output_file: string;
  processed_count: number;
  skipped_skus: string[];
  invalid_skus: string[];
  no_price_skus: string[];
  identity_skus: string[];
}

export interface FollowSellJobStatus {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  result: FollowSellResult | null;
  error: string | null;
}

export const followSellApi = {
  startProcess: async (req: FollowSellRequest): Promise<FollowSellJobStatus> => {
    const { data } = await axios.post<FollowSellJobStatus>('/api/follow-sell/process', req);
    return data;
  },

  pollStatus: async (jobId: string): Promise<FollowSellJobStatus> => {
    const { data } = await axios.get<FollowSellJobStatus>(`/api/follow-sell/status/${jobId}`);
    return data;
  },

  getDownloadUrl: (filename: string): string =>
    `/api/follow-sell/download/${encodeURIComponent(filename)}`,
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/services/followSellApi.ts
git commit -m "feat(follow-sell): add frontend API service"
```

---

### Task 7: FollowSell 页面

**Files:**
- Create: `frontend/src/pages/FollowSell.tsx`

- [ ] **Step 1: 创建页面组件**

```tsx
// frontend/src/pages/FollowSell.tsx
import { useState, useEffect, useRef } from 'react';
import axios from '../lib/axios';
import { followSellApi, FollowSellJobStatus } from '../services/followSellApi';
import { COUNTRIES } from '../constants/countries';

interface UploadedFiles {
  all_listings: string[];
  category_listings: string[];
}

export default function FollowSell() {
  const [country, setCountry] = useState('UK');
  const [allListingsFile, setAllListingsFile] = useState('');
  const [categoryFiles, setCategoryFiles] = useState<string[]>([]);
  const [skuText, setSkuText] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFiles>({ all_listings: [], category_listings: [] });
  const [jobStatus, setJobStatus] = useState<FollowSellJobStatus | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState('');
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // /api/excel/files 要求 country 参数
    axios.get<UploadedFiles>('/api/excel/files', { params: { country } })
      .then(r => setUploadedFiles(r.data));
  }, [country]);  // country 变化时重新加载文件列表

  useEffect(() => () => { if (pollRef.current) clearTimeout(pollRef.current); }, []);

  const countryConfig = COUNTRIES.find(c => c.code === country);
  const requiredCategoryCount = countryConfig?.categoryReportCount ?? 3;

  const poll = (jobId: string) => {
    pollRef.current = setTimeout(async () => {
      const status = await followSellApi.pollStatus(jobId);
      setJobStatus(status);
      if (status.status === 'running' || status.status === 'pending') {
        poll(jobId);
      } else {
        setIsRunning(false);
      }
    }, 1500);
  };

  const handleSubmit = async () => {
    setError('');
    const newSkus = skuText.split('\n').map(s => s.trim()).filter(Boolean);
    if (!allListingsFile) { setError('请选择 All Listings 文件'); return; }
    if (categoryFiles.length !== requiredCategoryCount) {
      setError(`${country} 需要选择 ${requiredCategoryCount} 张 Category 文件`); return;
    }
    if (newSkus.length === 0) { setError('请输入至少一个新款 SKU'); return; }

    setIsRunning(true);
    try {
      const job = await followSellApi.startProcess({
        country,
        all_listings_file: allListingsFile,
        category_files: categoryFiles,
        new_skus: newSkus,
      });
      setJobStatus(job);
      poll(job.job_id);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? '请求失败');
      setIsRunning(false);
    }
  };

  const toggleCategoryFile = (f: string) => {
    setCategoryFiles(prev =>
      prev.includes(f) ? prev.filter(x => x !== f) : [...prev, f]
    );
  };

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">跟卖上新</h1>

      {/* Step 1: 文件选择 */}
      <section className="bg-white rounded-lg border p-4 space-y-4">
        <h2 className="font-semibold text-gray-700">Step 1：选择数据文件</h2>

        <div>
          <label className="block text-sm text-gray-600 mb-1">国家</label>
          <select
            className="border rounded px-3 py-2 w-full"
            value={country}
            onChange={e => { setCountry(e.target.value); setCategoryFiles([]); }}
          >
            {COUNTRIES.map(c => (
              <option key={c.code} value={c.code}>{c.flag} {c.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm text-gray-600 mb-1">All Listings Report</label>
          <select
            className="border rounded px-3 py-2 w-full"
            value={allListingsFile}
            onChange={e => setAllListingsFile(e.target.value)}
          >
            <option value="">-- 请选择 --</option>
            {uploadedFiles.all_listings.map(f => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm text-gray-600 mb-1">
            Category Listings（需选 {requiredCategoryCount} 张，已选 {categoryFiles.length} 张）
          </label>
          <div className="space-y-1 max-h-40 overflow-y-auto border rounded p-2">
            {uploadedFiles.category_listings.map(f => (
              <label key={f} className="flex items-center gap-2 cursor-pointer text-sm">
                <input
                  type="checkbox"
                  checked={categoryFiles.includes(f)}
                  onChange={() => toggleCategoryFile(f)}
                />
                {f}
              </label>
            ))}
            {uploadedFiles.category_listings.length === 0 && (
              <p className="text-gray-400 text-sm">暂无已上传的 Category 文件</p>
            )}
          </div>
        </div>
      </section>

      {/* Step 2: 输入新款 SKU */}
      <section className="bg-white rounded-lg border p-4 space-y-2">
        <h2 className="font-semibold text-gray-700">Step 2：输入新款 SKU</h2>
        <p className="text-xs text-gray-400">每行一个，支持批量粘贴</p>
        <textarea
          className="border rounded px-3 py-2 w-full font-mono text-sm h-32 resize-none"
          placeholder={"EG02088BK04-UK1\nEG02088RD06-UK1\n..."}
          value={skuText}
          onChange={e => setSkuText(e.target.value)}
        />
      </section>

      {/* Step 3: 生成 */}
      <section className="bg-white rounded-lg border p-4 space-y-3">
        <h2 className="font-semibold text-gray-700">Step 3：生成跟卖表</h2>

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <button
          className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          onClick={handleSubmit}
          disabled={isRunning}
        >
          {isRunning ? '处理中...' : '生成跟卖表'}
        </button>

        {jobStatus && (jobStatus.status === 'running' || jobStatus.status === 'pending') && (
          <div className="space-y-1">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all"
                style={{ width: `${jobStatus.progress}%` }}
              />
            </div>
            <p className="text-sm text-gray-500">{jobStatus.progress}%</p>
          </div>
        )}

        {jobStatus?.status === 'completed' && jobStatus.result && (
          <div className="space-y-2">
            <p className="text-green-600 font-medium">
              ✅ 完成！生成 {jobStatus.result.processed_count} 行
            </p>
            <a
              href={followSellApi.getDownloadUrl(jobStatus.result.output_file)}
              className="inline-block bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 text-sm"
              download
            >
              下载跟卖表
            </a>
            {jobStatus.result.skipped_skus.length > 0 && (
              <details className="text-sm">
                <summary className="text-yellow-600 cursor-pointer">
                  ⚠️ 跳过 {jobStatus.result.skipped_skus.length} 条（映射/索引未命中）
                </summary>
                <ul className="mt-1 pl-4 text-gray-500">
                  {jobStatus.result.skipped_skus.map(s => <li key={s}>{s}</li>)}
                </ul>
              </details>
            )}
            {jobStatus.result.invalid_skus.length > 0 && (
              <details className="text-sm">
                <summary className="text-red-500 cursor-pointer">
                  ❌ 格式不合法 {jobStatus.result.invalid_skus.length} 条
                </summary>
                <ul className="mt-1 pl-4 text-gray-500">
                  {jobStatus.result.invalid_skus.map(s => <li key={s}>{s}</li>)}
                </ul>
              </details>
            )}
            {jobStatus.result.no_price_skus.length > 0 && (
              <p className="text-yellow-600 text-sm">
                ⚠️ 价格缺失跳过 {jobStatus.result.no_price_skus.length} 条
              </p>
            )}
            {jobStatus.result.identity_skus.length > 0 && (
              <p className="text-yellow-600 text-sm">
                ⚠️ 映射表中 {jobStatus.result.identity_skus.join(', ')} 新老款号相同，请核查
              </p>
            )}
          </div>
        )}

        {jobStatus?.status === 'failed' && (
          <p className="text-red-500 text-sm">❌ 处理失败：{jobStatus.error}</p>
        )}
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/FollowSell.tsx
git commit -m "feat(follow-sell): add FollowSell page component"
```

---

### Task 8: 接入现有 Tab 导航

**Files:**
- Modify: `frontend/src/App.tsx`

`App.tsx` 使用 `useState<TabKey>` 控制 tab 切换，不使用 React Router。新增"跟卖上新"tab，与现有"加色加码"/"颜色映射"/"下载历史"保持一致。

- [ ] **Step 1: 确认 TabKey 和 tabs 数组位置**

```bash
grep -n "TabKey\|tabs\|activeTab\|'process'\|'mapping'" frontend/src/App.tsx
```

- [ ] **Step 2: 修改 App.tsx，添加 follow-sell tab**

修改内容（根据 Step 1 的行号定位）：

1. 扩展 `TabKey` 类型：
```typescript
type TabKey = 'process' | 'mapping' | 'history' | 'follow-sell';
```

2. 在 `tabs` 数组中追加：
```typescript
{ key: 'follow-sell' as TabKey, label: '跟卖上新' },
```

3. 在 import 顶部添加：
```typescript
import FollowSell from './pages/FollowSell';
```

4. 在 tab 内容区域追加分支（找到 `activeTab === 'history'` 的位置后面）：
```tsx
) : activeTab === 'follow-sell' ? (
  <FollowSell />
) : null}
```

- [ ] **Step 3: 验证前端编译**

```bash
cd /Users/melodylu/PycharmProjects/Bu2_ama_ep/frontend
npm run build 2>&1 | tail -10
```

Expected: `built in` 无 ERROR

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(follow-sell): add route and nav entry for follow-sell page"
```

---

## 验收检查清单

- [ ] `python3 -m pytest backend/tests/test_follow_sell_processor.py -v` 全部通过
- [ ] 冒烟测试：输入 `EG02088BK04-UK1` 可生成含多行的 Excel 文件
- [ ] 下载的 Excel 中 `external_product_id` 列有 ASIN 值
- [ ] 下载的 Excel 中 `standard_price` = 老款价格 + 0.1
- [ ] 下载的 Excel 中所有 image 列为空
- [ ] 前端页面可访问 `/follow-sell`
- [ ] 前端 Step 1 的下拉框有已上传文件
- [ ] 生成完成后显示下载按钮和 processed_count
- [ ] Docker 重新 build 后功能正常

```bash
docker-compose build && docker-compose up -d
```
