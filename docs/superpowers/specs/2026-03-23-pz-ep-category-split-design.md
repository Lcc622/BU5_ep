# PZ/EP Category 分区上传设计

**日期：** 2026-03-23
**状态：** 已批准

---

## 背景

FR/DE/IT/ES 各有 PZ 和 EP 两个店铺账号，每账号有 2 个 category listing 文件（共 4 个）。
当前系统将所有 category 文件混在一个列表里，PZ 和 EP 文件原始名相同（如 `0_APPAREL-DRESS.xlsm`），
导致上传 EP 文件时会误删 PZ 的同名文件（清理 bug），且用户无法区分哪个文件属于哪个店铺。

前端的"删除"按钮已调用后端真实删除接口，因此更新文件的正确流程是：删旧文件 → 上传新文件。

---

## 目标

1. PZ 和 EP 文件在 UI 上分区显示，语义清晰
2. 上传同名文件只替换本店铺的旧版本，不影响另一个店铺
3. 后端文件命名携带店铺标识，便于区分和清理

---

## 不在本次范围内

- UK 不受影响（UK 没有 PZ/EP 分区，保持现有逻辑不变）
- 跟卖（FollowSell）页面的 category 上传暂不改动（跟卖目前不使用 category 文件）
- ES 尚未完整配置，但数据层改动对其透明适用

---

## 数据层设计

### 后端文件命名

上传 category 文件时，接口新增 `store_type: "pz" | "ep"` Form 参数。
文件保存路径格式变更：

```
旧：{COUNTRY}_category_{timestamp}_{original_name}
新：{COUNTRY}_category_{store_type}_{timestamp}_{original_name}
```

示例：
- `FR_category_pz_20260323050428_0_APPAREL-DRESS.xlsm`
- `FR_category_ep_20260323050416_0_APPAREL-DRESS.xlsm`

### 清理逻辑

恢复 `_cleanup_old_uploads`，但限定范围为**同 store_type + 同原始文件名**：
- 上传 PZ 新文件 → 删除同国家、同 `pz` 标签、同原始名的旧文件
- 上传 EP 新文件 → 仅删除同国家、同 `ep` 标签、同原始名的旧文件
- PZ 和 EP 文件互不干扰

### `/files` 接口返回格式

```json
{
  "all_listings": ["FR_all_listings_...txt"],
  "pz_category_listings": ["FR_category_pz_...xlsm"],
  "ep_category_listings": ["FR_category_ep_...xlsm"]
}
```

### ProcessRequest / FollowSellRequest

不变，仍使用 `category_files: list[str]`，前端发请求时合并两个数组：
```ts
category_files: [...pzCategoryFiles, ...epCategoryFiles]
```

---

## 前端设计

### Zustand Store（`useUploadStore.ts`）

每国 state 中 `categoryFiles: string[]` 拆分为：

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

`syncUploadedFiles` 改为从 `/files` 接口的 `pz_category_listings` / `ep_category_listings` 分别同步。

### FileUploader.tsx — Category 区域

原单一 Category 区域改为两个子区域，各自独立上传和删除：

```
┌─ Category Listings Reports ───────────────────────┐
│                                                    │
│  🏪 PZ 店铺（需 2 张）              [上传 PZ 文件] │
│  ├ 0_APPAREL-DRESS.xlsm               [删除]       │
│  └ 1_DRESS-SWEATER.xlsm               [删除]  ✓   │
│                                                    │
│  🏪 EP 店铺（需 2 张）              [上传 EP 文件] │
│  ├ 0_APPAREL-DRESS.xlsm               [删除]       │
│  └ 还需上传 1 张                                   │
└────────────────────────────────────────────────────┘
```

每个子区域：
- 有独立的 `<input type="file">` ref
- 满足 `categoryReportCount / 2` 张后显示"✓ 已满足"，仍可继续上传（不禁用）
- 删除调用 `excelApi.deleteUploadedFile(filename)` + 对应 store action

UK 保持原有单一区域（`required_category_reports = 3`，无 PZ/EP 分区）。

### ProcessButton.tsx

合并两个数组发请求（逻辑不变，只是数据来源改变）：
```ts
const allCategoryFiles = [...getPzCategoryFiles(country), ...getEpCategoryFiles(country)];
```

校验：`allCategoryFiles.length < 1` 时提示上传 category 文件（已放宽，不强制数量）。

### excelApi.ts

上传 category 接口新增 `store_type` 参数：
```ts
uploadCategoryFile(file: File, country: string, storeType: 'pz' | 'ep'): Promise<UploadResponse>
```

---

## 兼容性

- 历史已上传的旧格式文件（无 `pz`/`ep` 标签）在 `/files` 接口中返回到 `pz_category_listings`（默认归 PZ），前端 `syncUploadedFiles` 可识别并显示在 PZ 区域，用户可手动删除后重新上传
- 或者：历史文件不归类（两个区域均不显示），引导用户重新上传（更简洁，推荐）

---

## 改动文件清单

| 文件 | 改动类型 |
|------|---------|
| `backend/app/api/excel.py` | 上传接口加 `store_type` 参数；`_create_upload_path` 加 store_type；恢复 cleanup；`/files` 返回分类列表 |
| `backend/app/models/excel.py` | `UploadedFilesResponse` 新增 `pz_category_listings` / `ep_category_listings` |
| `frontend/src/store/useUploadStore.ts` | `categoryFiles` → `pzCategoryFiles` + `epCategoryFiles`；新增 actions；更新 sync |
| `frontend/src/components/ExcelUpload/FileUploader.tsx` | Category 区域拆成 PZ + EP 两块 |
| `frontend/src/components/ExcelProcess/ProcessButton.tsx` | 读取合并后的 category files |
| `frontend/src/services/excelApi.ts` | `uploadCategoryFile` 加 `storeType` 参数 |
| `frontend/src/types/api.ts` | `UploadedFilesResponse` 新增两个字段 |
| `backend/tests/test_*.py` | 无需改动（后端处理层不感知 store_type） |
