# FR/DE/IT/ES 跟卖上新扩展 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将跟卖上新功能从 UK 专用扩展为支持 FR/DE/IT/ES 五国，核心差异是 SKU 后缀规则和 scan 过滤逻辑。

**Architecture:** 修改 `parse_sku` 支持无后缀 SKU；在 processor 层按国家做输入归一化；去掉 scan 里的 UK 专用 `"-" in sku` 过滤，改为纯产品码前缀匹配；重构 `build_new_sku` 从解析结果重建而非截字符串拼接；修复 output_name 硬编码。

**Tech Stack:** Python 3.11, FastAPI, openpyxl, pytest

---

## 文件变更清单

| 操作 | 文件 | 变更内容 |
|------|------|---------|
| Modify | `backend/app/core/parsers/sku.py` | `SUFFIX_PATTERN` 可选匹配，`suffix: str \| None`，`parse_sku` 支持无后缀 SKU |
| Modify | `backend/app/core/processors/follow_sell_processor.py` | 新增 `normalize_sku_input()`；`scan_old_skus_by_prefix` 去掉 `-` 过滤；`build_new_sku` 改为基于解析结果重建；`output_name` 按国家命名 |
| Modify | `backend/app/models/follow_sell.py` | 更新字段说明（去掉"当前仅 UK"） |
| Modify | `backend/tests/test_follow_sell_processor.py` | 新增 EU 用例 |
| Modify | `backend/tests/test_listing_indexer.py` | 新增无后缀 SKU 进入 `by_prefix` 测试 |

---

## Task 1：`parse_sku` 支持无后缀 SKU

**Files:**
- Modify: `backend/app/core/parsers/sku.py`

### 变更说明

- `SUFFIX_PATTERN` 改为 `r"(-[A-Z]{2}\d?)$"` → 新增独立函数尝试匹配可选后缀
- `SKUInfo.suffix: str | None`（`None` 表示无后缀，原来是必填字符串）
- `parse_sku` 先尝试匹配后缀，匹配不到则 `suffix=None`，base 取全部字符串

- [ ] **Step 1：写失败测试**

```python
# backend/tests/test_follow_sell_processor.py 末尾追加
from app.core.parsers.sku import parse_sku as _parse_sku

def test_parse_sku_no_suffix():
    """FR/DE/IT/ES 无后缀 SKU 能正常解析，suffix 为 None。"""
    info = _parse_sku("EG02084BK04")
    assert info.product_code == "EG02084"
    assert info.color_code == "BK"
    assert info.size_code == "04"
    assert info.suffix is None

def test_parse_sku_co_suffix():
    """-CO 后缀 SKU 正常解析。"""
    info = _parse_sku("EG02084BK04-CO")
    assert info.suffix == "-CO"

def test_parse_sku_uk1_still_works():
    """-UK1 后缀不受影响（向后兼容）。"""
    info = _parse_sku("EG02088BK04-UK1")
    assert info.suffix == "-UK1"
```

- [ ] **Step 2：运行确认失败**

```bash
cd backend && python3 -m pytest tests/test_follow_sell_processor.py::test_parse_sku_no_suffix -v
```
预期：FAIL（`ValueError: Invalid SKU suffix format`）

- [ ] **Step 3：实现**

```python
# backend/app/core/parsers/sku.py
"""SKU 解析器。"""
from __future__ import annotations
from dataclasses import dataclass
import re

SUFFIX_PATTERN = re.compile(r"(-[A-Z]{2}\d?)$")


@dataclass(frozen=True, slots=True)
class SKUInfo:
    product_code: str
    color_code: str
    size_code: str
    suffix: str | None   # None = 无后缀（FR/DE/IT/ES 无尾缀 SKU）
    raw_sku: str


def parse_sku(raw_sku: str) -> SKUInfo:
    """解析欧洲站 SKU，支持 7/8 位产品码，后缀可选。"""
    sku = raw_sku.strip().upper()
    if not sku:
        raise ValueError("SKU cannot be empty")

    suffix_match = SUFFIX_PATTERN.search(sku)
    if suffix_match:
        suffix: str | None = suffix_match.group(0)
        base = sku[: suffix_match.start()]
    else:
        suffix = None
        base = sku

    if len(base) < 11:
        raise ValueError(f"SKU base too short: {raw_sku!r}")

    size_code = base[-2:]
    color_code = base[-4:-2]
    product_code = base[:-4]

    if len(product_code) not in (7, 8):
        raise ValueError(f"Unsupported product code length: {raw_sku!r}")
    if not product_code.isalnum():
        raise ValueError(f"Invalid product code: {raw_sku!r}")
    if not color_code.isalpha():
        raise ValueError(f"Invalid color code: {raw_sku!r}")
    if not size_code.isdigit():
        raise ValueError(f"Invalid size code: {raw_sku!r}")

    return SKUInfo(
        product_code=product_code,
        color_code=color_code,
        size_code=size_code,
        suffix=suffix,
        raw_sku=raw_sku,
    )
```

- [ ] **Step 4：运行确认通过**

```bash
cd backend && python3 -m pytest tests/test_follow_sell_processor.py::test_parse_sku_no_suffix tests/test_follow_sell_processor.py::test_parse_sku_co_suffix tests/test_follow_sell_processor.py::test_parse_sku_uk1_still_works -v
```
预期：3 PASSED

- [ ] **Step 5：全量测试**

```bash
cd backend && python3 -m pytest -v
```
预期：全部通过（已有测试不受影响）

- [ ] **Step 6：Commit**

```bash
git add backend/app/core/parsers/sku.py backend/tests/test_follow_sell_processor.py
git commit -m "feat(parser): support optional suffix in parse_sku, suffix=None for no-suffix SKUs"
```

---

## Task 2：`normalize_sku_input` 按国家归一化输入

**Files:**
- Modify: `backend/app/core/processors/follow_sell_processor.py`

### 变更说明

将当前 `rstrip("+")` 拆成独立函数，UK 特有，EU 只做 strip。

- [ ] **Step 1：写测试**

```python
# backend/tests/test_follow_sell_processor.py
from app.core.processors.follow_sell_processor import normalize_sku_input
from app.config import Country

def test_normalize_uk_strips_plus():
    assert normalize_sku_input("EG02088BK04-UK1+", Country.UK) == "EG02088BK04-UK1"

def test_normalize_uk_no_plus_unchanged():
    assert normalize_sku_input("EG02088BK04-UK1", Country.UK) == "EG02088BK04-UK1"

def test_normalize_fr_no_change():
    """FR 无后缀 SKU 不做特殊处理，只 strip。"""
    assert normalize_sku_input("  EG02088BK04  ", Country.FR) == "EG02088BK04"

def test_normalize_fr_co_suffix_unchanged():
    assert normalize_sku_input("EG02088BK04-CO", Country.FR) == "EG02088BK04-CO"
```

- [ ] **Step 2：运行确认失败**

```bash
cd backend && python3 -m pytest tests/test_follow_sell_processor.py::test_normalize_uk_strips_plus -v
```
预期：FAIL（`ImportError: cannot import name 'normalize_sku_input'`）

- [ ] **Step 3：实现**

在 `follow_sell_processor.py` 顶部（`load_product_mapping` 之前）新增：

```python
def normalize_sku_input(raw: str, country: Any) -> str:
    """按国家规范化新款 SKU 输入。
    UK: -UK1+ → -UK1（去掉末尾 +）
    FR/DE/IT/ES: 仅去首尾空白
    """
    stripped = raw.strip()
    from app.config import Country as _C
    if country == _C.UK:
        return stripped.rstrip("+")
    return stripped
```

同时在 `process()` 里把：
```python
normalized = raw.strip().rstrip("+")
```
改为：
```python
normalized = normalize_sku_input(raw, request.country)
```

- [ ] **Step 4：全量测试通过**

```bash
cd backend && python3 -m pytest -v
```

- [ ] **Step 5：Commit**

```bash
git add backend/app/core/processors/follow_sell_processor.py backend/tests/test_follow_sell_processor.py
git commit -m "feat(follow-sell): extract normalize_sku_input with country-aware suffix normalization"
```

---

## Task 3：`build_new_sku` 从解析结果重建（不再截字符串）

**Files:**
- Modify: `backend/app/core/processors/follow_sell_processor.py`

### 变更说明

当前实现：`new_product_code + old_sku[len(old_pc):] + suffix`
问题：老款带 `-CO` 时 `rest` 已含后缀，再拼 `suffix` 会变成 `-CO-CO`

新实现：接受解析后的 `SKUInfo`，用 `new_product_code + color_code + size_code + (suffix or "")` 重建。

- [ ] **Step 1：写测试**

```python
from app.core.processors.follow_sell_processor import build_new_sku
from app.core.parsers.sku import parse_sku

def test_build_new_sku_uk():
    old_info = parse_sku("EG02084BK04-UK1")
    # UK: 用新款输入的 suffix
    result = build_new_sku(old_info, "EG02084", "EG02088", "-UK1")
    assert result == "EG02088BK04-UK1"

def test_build_new_sku_no_suffix():
    """FR/DE/IT/ES 无后缀老款 → 新款也无后缀。"""
    old_info = parse_sku("EG02084BK04")
    result = build_new_sku(old_info, "EG02084", "EG02088", None)
    assert result == "EG02088BK04"

def test_build_new_sku_co_suffix():
    """-CO 后缀老款 → 新款也是 -CO，不重复。"""
    old_info = parse_sku("EG02084BK04-CO")
    result = build_new_sku(old_info, "EG02084", "EG02088", "-CO")
    assert result == "EG02088BK04-CO"
```

- [ ] **Step 2：运行确认失败**

```bash
cd backend && python3 -m pytest tests/test_follow_sell_processor.py::test_build_new_sku_no_suffix -v
```
预期：FAIL（函数签名不匹配）

- [ ] **Step 3：实现**

```python
# 替换 build_new_sku 函数
def build_new_sku(old_info: "SKUInfo", old_product_code: str, new_product_code: str, target_suffix: str | None) -> str:
    """从解析结果重建新款 SKU。

    Args:
        old_info: 老款 SKU 的解析结果（提供 color_code、size_code）
        old_product_code: 老款产品码（仅用于校验）
        new_product_code: 新款产品码
        target_suffix: 目标后缀（UK 为 '-UK1'，FR/DE/IT/ES 无后缀为 None）
    """
    suffix_str = target_suffix or ""
    return f"{new_product_code.upper()}{old_info.color_code}{old_info.size_code}{suffix_str}"
```

同时更新 `process()` 里的调用：
```python
# 旧：new_sku = build_new_sku(old_sku_raw, old_pc, new_pc, suffix)
# 新（需要先解析 old_sku_raw）：
old_parsed = self._parse_old_sku(old_sku_raw)  # 见下方
new_sku = build_new_sku(old_parsed, old_pc, new_pc, target_suffix)
```

其中 `target_suffix` 从新款 SKU 解析得到（`info.suffix`，可为 None）。

- [ ] **Step 4：全量测试通过**

```bash
cd backend && python3 -m pytest -v
```

- [ ] **Step 5：Commit**

```bash
git add backend/app/core/processors/follow_sell_processor.py backend/tests/test_follow_sell_processor.py
git commit -m "refactor(follow-sell): rebuild new SKU from parsed components, fix -CO double-suffix bug"
```

---

## Task 4：`scan_old_skus_by_prefix` 去掉 UK 专用过滤

**Files:**
- Modify: `backend/app/core/processors/follow_sell_processor.py`

### 变更说明

当前 `if "-" in upper_sku: continue` 是 UK 专用逻辑（老款无后缀，凡含 `-` 的是新款）。EU 老款可能有 `-CO`，不能用此规则。

正确做法：只靠 `old_product_code + color_code` 前缀匹配。只要前缀对，就是老款。新款（`new_product_code + color_code`）因产品码不同，天然不会命中老款前缀扫描。

- [ ] **Step 1：写测试**

```python
def test_scan_includes_co_suffix_old_skus():
    """EU 场景：old SKU 带 -CO 后缀，scan 不应排除。"""
    index = {
        "by_sku": {
            "EG02084BK04-CO": {
                "merged_data": {"seller-sku": "EG02084BK04-CO", "price": "39.99"},
                "all_listings_data": {"seller-sku": "EG02084BK04-CO", "price": "39.99"},
                "category_data": None,
            },
            "EG02084BK06-CO": {
                "merged_data": {"seller-sku": "EG02084BK06-CO", "price": "39.99"},
                "all_listings_data": {"seller-sku": "EG02084BK06-CO", "price": "39.99"},
                "category_data": None,
            },
            "EG02088BK04-CO": {  # 新款，不应被扫到
                "merged_data": {"seller-sku": "EG02088BK04-CO", "price": "40.09"},
                "all_listings_data": {"seller-sku": "EG02088BK04-CO", "price": "40.09"},
                "category_data": None,
            },
        }
    }
    results = scan_old_skus_by_prefix(index, "EG02084", "BK")
    skus = [r.get("seller-sku") for r in results]
    assert "EG02084BK04-CO" in skus
    assert "EG02084BK06-CO" in skus
    assert "EG02088BK04-CO" not in skus  # 新款产品码不匹配，天然排除
```

- [ ] **Step 2：运行确认失败**

```bash
cd backend && python3 -m pytest tests/test_follow_sell_processor.py::test_scan_includes_co_suffix_old_skus -v
```
预期：FAIL（`-CO` SKU 被 `-` 过滤排除，结果为空）

- [ ] **Step 3：实现**

```python
def scan_old_skus_by_prefix(
    index: dict[str, Any],
    old_product_code: str,
    color_code: str,
) -> list[dict[str, Any]]:
    """在 by_sku 索引中按前缀扫描老款 SKU 行。

    只匹配 old_product_code + color_code 前缀的 SKU。
    不再依赖 '-' 过滤：产品码本身已经能区分老款和新款。
    """
    prefix = (old_product_code + color_code).upper()
    by_sku: dict[str, Any] = index.get("by_sku", {}) if isinstance(index, dict) else {}
    results = []
    for raw_sku, entry in by_sku.items():
        upper_sku = raw_sku.upper()
        if not upper_sku.startswith(prefix):
            continue
        if not isinstance(entry, dict):
            continue
        flat = entry.get("merged_data") or entry.get("all_listings_data") or {}
        if flat:
            results.append(flat)
    return results
```

- [ ] **Step 4：全量测试通过**

```bash
cd backend && python3 -m pytest -v
```

- [ ] **Step 5：Commit**

```bash
git add backend/app/core/processors/follow_sell_processor.py backend/tests/test_follow_sell_processor.py
git commit -m "fix(follow-sell): remove UK-specific '-' filter from scan, rely on product code prefix only"
```

---

## Task 5：修复 output_name 硬编码 + 模型注释

**Files:**
- Modify: `backend/app/core/processors/follow_sell_processor.py`
- Modify: `backend/app/models/follow_sell.py`

- [ ] **Step 1：修改 output_name**

```python
# 旧
output_name = f"UK-跟卖上新-{timestamp}.xlsx"
# 新
output_name = f"{request.country.value}-跟卖上新-{timestamp}.xlsx"
```

- [ ] **Step 2：更新模型注释**

```python
# follow_sell.py
country: CountryEnum = Field(..., description="目标国家（UK / FR / DE / IT / ES）")
```

- [ ] **Step 3：全量测试**

```bash
cd backend && python3 -m pytest -v
```

- [ ] **Step 4：Commit**

```bash
git add backend/app/core/processors/follow_sell_processor.py backend/app/models/follow_sell.py
git commit -m "fix(follow-sell): use country code in output filename, update model description"
```

---

## Task 6：`process()` 集成 —— 传入 old_parsed 和 target_suffix

**Files:**
- Modify: `backend/app/core/processors/follow_sell_processor.py`

### 说明

把 Task 1-4 的变更在 `process()` 主流程里串起来。需要：
1. 解析老款 SKU（用新的 `parse_sku`，支持无后缀）
2. `target_suffix` 从新款 `info.suffix` 获取
3. 传给 `build_new_sku`

- [ ] **Step 1：更新 process() 调用链**

在 `for old_row in old_rows:` 循环内：

```python
old_sku_raw = str(old_row.get("seller-sku") or old_row.get("sku") or "").strip().upper()
if not old_sku_raw:
    continue

# 解析老款 SKU（支持无后缀）
try:
    old_parsed = parse_sku(old_sku_raw)
except ValueError:
    # 无法解析的老款 SKU（格式异常），跳过
    no_price_skus.append(old_sku_raw)
    continue

old_price_raw = old_row.get("price") or old_row.get("standard_price")
try:
    new_price, list_price = calculate_prices(old_price_raw)
except ValueError:
    no_price_skus.append(old_sku_raw)
    continue

new_sku = build_new_sku(old_parsed, old_pc, new_pc, suffix)  # suffix 来自新款 info.suffix
```

- [ ] **Step 2：全量测试**

```bash
cd backend && python3 -m pytest -v
```

- [ ] **Step 3：Commit**

```bash
git add backend/app/core/processors/follow_sell_processor.py
git commit -m "feat(follow-sell): wire parse_sku + build_new_sku into process(), support EU no-suffix flow"
```

---

## 最终验收

- [ ] 全量测试通过：`cd backend && python3 -m pytest -v`（31+ passed）
- [ ] UK 回归：`EG02088BK04-UK1` 输入仍正常生成跟卖表
- [ ] FR/DE/IT/ES 无后缀 SKU：`EG02088BK04` 输入能解析、scan、生成
- [ ] `-CO` 后缀 SKU：`EG02088BK04-CO` 不会产生双后缀
- [ ] 输出文件名：`FR-跟卖上新-{timestamp}.xlsx`（非 UK 不再硬编码 UK）

---

## 风险点备注

| 风险 | 说明 |
|------|------|
| `ListingIndexer` 行为变化 | `parse_sku` 支持无后缀后，原来进 `unparsed_rows` 的无后缀 SKU 会进入 `by_prefix`，属于预期变化，EU 数据索引更准确 |
| UK scan 回归 | 去掉 `-` 过滤后，UK 场景下 `EG02084BK04-UK1` 理论上会被老款 scan 扫到，但 `EG02084BK` 前缀 + `EG02084BK04-UK1` 确实前缀匹配，会误扫。**需验证**：UK 的 All Listings 里老款是否真的只有无后缀 SKU（EG02084BK04，无 -UK1）。如果有，需要针对 UK 保留后缀排除逻辑 |
