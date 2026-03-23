# PZ/EP Category 分区上传设计

**日期：** 2026-03-23
**状态：** 已批准

---

## 背景

FR/DE/IT/ES 各有 PZ 和 EP 两个店铺账号，每账号有 2 个 category listing 文件（共 4 个）。
当前系统将所有 category 文件混在一个列表里，PZ 和 EP 文件原始名相同（如 `0_APPAREL-DRESS.xlsm`），
导致上传 EP 文件时会误删 PZ 的同名文件，且用户无法区分哪个文件属于哪个店铺。

前端"删除"按钮已调用后端真实删除接口，因此更新文件的正确流程是：删旧文件 → 上传新文件。

---

## 目标

1. PZ 和 EP 文件在 UI 上分区显示，语义清晰
2. 上传同名文件只替换本店铺的旧版本，不影响另一个店铺
3. 后端文件命名携带店铺标识，便于区分和清理

---

## 不在本次范围内

- UK 不受影响（无 PZ/EP 分区，保持现有逻辑不变）
- FollowSell 页面的 category 上传暂不改动（跟卖目前不使用 category 文件）

---

## 后端设计

### 1. 上传接口（`POST /api/excel/upload/category`）

新增 `store_type: Literal["pz", "ep"]` Form 参数（后端用 Pydantic Literal 或显式校验，非法值返回 422）。

文件保存路径格式变更：

```
旧：{COUNTRY}_category_{timestamp}_{original_name}
新：{COUNTRY}_category_{store_type}_{timestamp}_{original_name}
```

示例：
- `FR_category_pz_20260323050428_0_APPAREL-DRESS.xlsm`
- `FR_category_ep_20260323050416_0_APPAREL-DRESS.xlsm`

上传接口调用 `_cleanup_old_uploads` 时，prefix 传入 `f"category_{store_type}"`（即 `"category_pz"` 或 `"category_ep"`），这样 glob 模式为 `{COUNTRY}_category_{store_type}_*`，两个店铺文件互不干扰。

`_create_upload_path` 和 `_extract_original_upload_name` 已经通过 prefix 参数工作——prefix 变为 `"category_pz"` 后，文件名中 `{COUNTRY}_category_pz_` 之后的部分仍然是 `{timestamp}_{original_name}`，现有的 14 位时间戳解析逻辑不变。

### 2. `_validate_process_files`（无需修改）

现有校验：
```python
if f"{request.country.value}_category_" not in category_path.name:
```
新格式文件名 `FR_category_pz_...` 仍包含 `FR_category_` 子串，校验继续通过，无需改动。

### 3. `/files` 接口返回格式

`UploadedFilesResponse` 新增两个字段（原 `category_listings` 字段**移除**）：

```python
class UploadedFilesResponse(BaseModel):
    all_listings: list[str]
    pz_category_listings: list[str]
    ep_category_listings: list[str]
```

**历史文件兼容策略（Option B）：** 不携带 `store_type` 标签的旧格式文件（如 `FR_category_20260323_0_APPAREL-DRESS.xlsm`）**不归入任何分区**，两个区域均不显示。用户在升级后需重新上传全部 category 文件。这避免了文件名模式检测的脆弱性，行为简单明确。

`_list_uploaded_files` 调用时分别传 `"category_pz"` 和 `"category_ep"` 作为 prefix，自动只列出带对应标签的文件。

---

## 前端设计

### 1. `countries.ts`

每个国家条目新增 `perStoreCategoryCount` 字段（明确，避免 `categoryReportCount / 2` 的隐式计算）：

```ts
{ code: 'FR', ..., categoryReportCount: 4, perStoreCategoryCount: 2 }
{ code: 'DE', ..., categoryReportCount: 4, perStoreCategoryCount: 2 }
{ code: 'IT', ..., categoryReportCount: 4, perStoreCategoryCount: 2 }
{ code: 'ES', ..., categoryReportCount: 4, perStoreCategoryCount: 2 }
{ code: 'UK', ..., categoryReportCount: 3, perStoreCategoryCount: 0 }
// UK perStoreCategoryCount: 0 表示不分区，使用单一区域
```

### 2. Zustand Store（`useUploadStore.ts`）

每国 state 中 `categoryFiles: string[]` 替换为：

```ts
pzCategoryFiles: string[]
epCategoryFiles: string[]
```

新增 actions：
- `addPzCategoryFile(country, filename)`
- `removePzCategoryFile(country, filename)`
- `addEpCategoryFile(country, filename)`
- `removeEpCategoryFile(country, filename)`
- `getPzCategoryFiles(country)` / `getEpCategoryFiles(country)`

`syncUploadedFiles` 从 `/files` 接口读取 `pz_category_listings` / `ep_category_listings`，分别与 store 中对应数组对比，合并生成一个 `missingCategoryFiles: string[]`（PZ 和 EP 缺失文件合并在一起），仍通过 toast 提示用户。`pzCategoryFiles` 和 `epCategoryFiles` 必须在单次 `set(...)` 调用中原子更新，避免状态闪烁。

**Zustand persist 版本升级：** 将 persist 配置的 `version` 从当前值 +1，添加 `migrate` 函数，将旧的 `categoryFiles` 字段清空（不迁移到 pz/ep，因为旧文件也不会显示在新 UI 中）。

### 3. `FileUploader.tsx` — Category 区域

UK（`perStoreCategoryCount === 0`）保持现有单一区域不变。UK 上传 category 文件时 `store_type` 固定传 `"pz"`，文件存为 `UK_category_pz_*`，前端读取 `pzCategoryFiles` 显示在单一区域（`epCategoryFiles` 对 UK 始终为空）。

FR/DE/IT/ES（`perStoreCategoryCount > 0`）拆成两个子区域，各自独立：

```
┌─ Category Listings Reports ────────────────────────┐
│                                                     │
│  🏪 PZ 店铺（需 2 张）             [上传 PZ 文件]  │
│  ├ 0_APPAREL-DRESS.xlsm               [删除]        │
│  └ 1_DRESS-SWEATER.xlsm               [删除]  ✓    │
│                                                     │
│  🏪 EP 店铺（需 2 张）             [上传 EP 文件]  │
│  ├ 0_APPAREL-DRESS.xlsm               [删除]        │
│  └ 还需上传 1 张                                    │
└─────────────────────────────────────────────────────┘
```

每个子区域：
- 有独立的 `<input type="file">` ref，上传时携带对应 `store_type`
- 达到 `perStoreCategoryCount` 张后显示"✓ 已满足"，仍可继续上传（不禁用按钮）
- 删除调用 `excelApi.deleteUploadedFile(filename)` + 对应 store action

### 4. `excelApi.ts`

上传 category 接口新增 `storeType` 参数：
```ts
uploadCategoryFile(file: File, country: string, storeType: 'pz' | 'ep'): Promise<UploadResponse>
```

### 5. `ProcessButton.tsx`

- 合并两个数组发请求：`category_files: [...getPzCategoryFiles(country), ...getEpCategoryFiles(country)]`
- 校验：`totalCategoryFiles < 1` 时提示上传 category 文件
- 显示计数更新为合并格式：`{pzCount + epCount}/{categoryReportCount}`

### 6. `types/api.ts`

`UploadedFilesResponse` 新增字段（移除 `category_listings`）：
```ts
interface UploadedFilesResponse {
  all_listings: string[]
  pz_category_listings: string[]
  ep_category_listings: string[]
}
```

---

## 改动文件清单

| 文件 | 改动内容 |
|------|---------|
| `backend/app/api/excel.py` | 上传接口加 `store_type` 参数；`_create_upload_path` 传 `f"category_{store_type}"`；恢复 cleanup；`/files` 返回 pz/ep 分类列表 |
| `backend/app/models/excel.py` | `UploadedFilesResponse` 新增 `pz_category_listings` / `ep_category_listings`，移除 `category_listings` |
| `frontend/src/constants/countries.ts` | 新增 `perStoreCategoryCount` 字段 |
| `frontend/src/store/useUploadStore.ts` | `categoryFiles` → `pzCategoryFiles` + `epCategoryFiles`；新增 actions；更新 sync；persist version +1 + migrate |
| `frontend/src/components/ExcelUpload/FileUploader.tsx` | EU 国家 Category 区域拆成 PZ + EP 两块；UK 保持原样 |
| `frontend/src/components/ExcelProcess/ProcessButton.tsx` | 合并两数组；更新显示计数 |
| `frontend/src/services/excelApi.ts` | `uploadCategoryFile` 加 `storeType` 参数 |
| `frontend/src/types/api.ts` | `UploadedFilesResponse` 字段更新 |
| `backend/tests/test_*.py` | 无需改动（处理层不感知 store_type） |
