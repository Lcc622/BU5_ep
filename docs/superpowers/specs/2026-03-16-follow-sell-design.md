# 跟卖上新功能设计文档

**日期**: 2026-03-16
**范围**: UK 站（先打通，后扩展 FR/DE/IT/ES）
**参考文档**: `docs/跟卖SOP梳理.md`

---

## 一、目标

在新版本 SKU 入库后，半自动批量生成跟卖上新模板，实现：
- 新老版本同时在购物车
- 新版本价格高于老版本 £0.1，老版本优先出单
- 自动补全同色所有尺码，防止漏码导致变体结构异常

---

## 二、整体架构

### 新增文件

```
backend/app/
  api/follow_sell.py                     # 路由：触发、轮询、下载
  core/processors/follow_sell_processor.py  # 核心处理逻辑
  models/follow_sell.py                  # Pydantic 请求/响应模型

frontend/src/
  pages/FollowSell.tsx                   # 跟卖页面（3步流程）
  services/followSellApi.ts             # API 调用层
```

### 复用现有模块

| 模块 | 用途 |
|------|------|
| `ListingIndexer` | 解析 All Listings + Category Listings，构建 SKU 索引 |
| `parse_sku()` | 解析新款 SKU（用户输入），提取 product_code / color_code / suffix；仅限用户输入，不用于老款 SKU |
| `UPLOADS_DIR` / `RESULTS_DIR` | 文件路径常量 |
| `COUNTRY_PROFILES` | 模板文件名、marketplace_id |
| `/api/excel/files` | 前端文件下拉列表直接复用此接口，不需要新建文件列表 API |

### 模板路径说明

UK 模板实际位于 `templates/AMZEU_UK_AddColor_Template.xlsx`（项目根目录下），
不在 `backend/templates/`。`CountryProfile.template_file` 存的是文件名，需配合正确的基础路径使用。

### 固定数据文件

映射表固定路径：`backend/uploads/新老款映射信息(1).xlsx`
格式：两列 `老款号`（old_product_code） / `新款号`（new_product_code）

---

## 三、核心数据流

```
用户粘贴新款 SKU（批量，每行一个）
↓
parse_sku() → 提取 new_product_code + color_code + suffix
  按 (new_product_code, color_code) 去重 → 每个唯一颜色组独立处理
  （多色输入如 BK + PK → 两组独立扩展，均生成完整输出）
↓
查映射表: new_product_code → old_product_code
  - 找不到 → warning，跳过该颜色组
  - old_product_code == new_product_code → warning（疑似映射表录入错误），继续处理
  - 空行/None → 跳过
↓
在 ListingIndexer 的 by_sku 中做前缀扫描：
  old_sku_prefix = old_product_code + color_code（如 "EG02084BK"）
  匹配规则: raw_sku.startswith(old_sku_prefix)
  ⚠️  注意：老款 SKU 在 All Listings 中无国家后缀（如 EG02084BK04，非 EG02084BK04-UK1）
      不能用 parse_sku()，直接按字符串前缀匹配 by_sku 字典
  → 自动扩展为该颜色下的全部老款 SKU（所有尺码）
↓
对每条老款 SKU 生成新款 SKU：
  new_sku = new_product_code + old_color_code + old_size_code + suffix
  suffix 取自用户输入的新款 SKU（parse_sku 解析结果，如 "-UK1"）
  示例: EG02084BK04 + suffix "-UK1" → new_sku = EG02088BK04-UK1
↓
每条老款 SKU 生成一行输出：
  - 9 个必改字段（见下）
  - 其余字段从 Category Listings Report 老款行复制
↓
写入 UK 模板（AMZEU_UK_AddColor_Template.xlsx）→ 输出 Excel
```

---

## 四、字段生成规则

### 9 个必改字段（已核对模板真实列名）

| 模板机器列名 | 显示名 | 来源 | 规则 |
|------------|--------|------|------|
| `item_sku` | Seller SKU | 计算生成 | old_sku 中 old_product_code → new_product_code 替换，拼接 suffix |
| `external_product_id` | Product ID | All Listings `asin1` | 老款 ASIN |
| `external_product_id_type` | Product ID Type | 固定 | `"ASIN"` |
| `model` | Model Number | 同 item_sku | — |
| `part_number` | Manufacturer Part Number | 同 item_sku | — |
| `standard_price` | Standard Price (col 26) | All Listings `price` | `round(old_price + 0.1, 2)`；若 price 缺失则跳过整行并 warning（不得回落 0） |
| `list_price` | Recommended Retail Price (col 154) | standard_price | `round(standard_price + 10, 2)` |
| `quantity` | Quantity | 固定 | `2` |
| `main_image_url` + `other_image_url1~8` | 所有图片列（共 9 列） | 固定 | `""` 全部清空 |

### 其他字段

全部从 **Category Listings Report** 中的老款 SKU 行复制，不做任何修改。
包括：标题、五点、描述、类目、变体结构、品牌、颜色属性、尺码属性、材质等。

### 9 个 image 列（全部清空）

UK 模板共有以下 9 个 image 列，跟卖时全部置空：
`main_image_url`, `other_image_url1`, `other_image_url2`, `other_image_url3`,
`other_image_url4`, `other_image_url5`, `other_image_url6`, `other_image_url7`, `other_image_url8`

实现时统一处理所有列名包含 `"image"` 的列，防止遗漏。

### 自动补全尺码逻辑

**关键约束**（来自 SOP ⚠️ 现存问题）：用户输入的 SKU 可能只是 BI 显示入库的部分，但必须对该颜色下所有老款 SKU 都生成跟卖行。

```python
# 输入: ["EG02088BK04-UK1"]
# parse_sku → new_product_code=EG02088, color_code=BK, suffix="-UK1"
# 查映射: EG02088 → EG02084
# by_sku 前缀扫描: 匹配所有 key.startswith("EG02084BK") 的条目
# 结果老款: EG02084BK02, EG02084BK04, EG02084BK06, ... (全部尺码，无后缀)
# 生成新款: EG02088BK02-UK1, EG02088BK04-UK1, EG02088BK06-UK1, ...
```

---

## 五、API 设计

### 后端路由 `/api/follow-sell`

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/follow-sell/process` | 触发异步处理，返回 job_id |
| `GET` | `/api/follow-sell/status/{job_id}` | 轮询任务状态 |
| `GET` | `/api/follow-sell/download/{filename}` | 下载结果文件 |

### 请求体（ProcessRequest）

```python
class FollowSellRequest(BaseModel):
    country: Country                  # 目标国家（当前仅 UK）
    all_listings_file: str            # 已上传的 All Listings 文件名
    category_files: list[str]         # 已上传的 Category Listings 文件名
    new_skus: list[str]               # 用户输入的新款 SKU 列表
```

### 响应模型

```python
class FollowSellResult(BaseModel):
    output_file: str
    processed_count: int              # 生成的行数
    skipped_skus: list[str]           # 映射表找不到 / 老款无索引命中（warning）
    invalid_skus: list[str]           # 格式不合法无法 parse_sku（warning）
    no_price_skus: list[str]          # All Listings 中 price 缺失（warning，该行跳过）
    identity_skus: list[str]          # old_code == new_code 的疑似异常映射（warning）

class FollowSellJobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    progress: int                     # 0-100
    result: FollowSellResult | None
    error: str | None
```

---

## 六、前端设计

### 路由

新增 `/follow-sell`，在顶部 Nav 增加"跟卖上新"入口。

### 页面结构（3 步流程）

**Step 1 - 选择数据文件**
- All Listings 下拉（从已上传文件中选）
- Category Listings 多选（从已上传文件中选，UK 需 3 张）

**Step 2 - 输入新款 SKU**
- Textarea，每行一个 SKU，支持批量粘贴

**Step 3 - 生成**
- "生成跟卖表"按钮
- 异步处理，显示进度条（polling，与加色加码一致）
- 完成：显示行数 + 下载按钮
- 警告：列出映射表中找不到的 SKU

### 状态管理

新建 `useFollowSellStore`（Zustand），独立于现有 `useProcessStore`。

---

## 七、错误处理

| 情况 | 处理方式 |
|------|---------|
| SKU 格式不合法（无法 parse_sku） | 解析失败，记录错误，跳过，其余正常处理 |
| SKU 在映射表找不到 | 记录 warning（skipped_skus），跳过该颜色组 |
| old_product_code == new_product_code | 记录 warning（identity_skus），继续处理 |
| 映射表空行 / None 值 | 跳过 |
| 老款 SKU 前缀扫描无结果 | 记录 warning，跳过该颜色组 |
| 映射文件不存在 | 400 错误，提示用户上传映射文件 |

---

## 八、范围限制（不在本次实现）

- FR / DE / IT / ES 国家（二期扩展）
- 映射文件的前端上传/管理界面（当前手动放到 uploads 目录）
- 与 BI 系统的自动对接
