# PZ/EP Category 分区上传 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 category 文件上传区域按 PZ/EP 店铺分区，文件名携带店铺标识，两个店铺互不干扰。

**Architecture:** 后端上传接口新增 `store_type` Form 参数，文件保存为 `{COUNTRY}_category_{pz|ep}_{timestamp}_{name}`，`/files` 接口分别返回 `pz_category_listings` 和 `ep_category_listings`；前端 store 拆分 `categoryFiles` 为 `pzCategoryFiles` + `epCategoryFiles`，FileUploader 为 EU 国家渲染两个独立子区域，UK 保持单一区域不变。

**Tech Stack:** FastAPI + Pydantic (backend), React + TypeScript + Zustand (frontend)

---

## 文件改动清单

| 文件 | 操作 |
|------|------|
| `backend/app/models/excel.py` | 修改 `UploadedFilesResponse`：移除 `category_listings`，新增 `pz_category_listings` / `ep_category_listings` |
| `backend/app/api/excel.py` | `upload_category` 加 `store_type` Form 参数；恢复 scoped `_cleanup_old_uploads`；`/files` 分别 list pz/ep |
| `frontend/src/types/api.ts` | `UploadedFilesResponse`：移除 `category_listings`，新增 `pz_category_listings` / `ep_category_listings` |
| `frontend/src/constants/countries.ts` | 各条目新增 `perStoreCategoryCount` 字段 |
| `frontend/src/store/useUploadStore.ts` | `categoryFiles` → `pzCategoryFiles` + `epCategoryFiles`；新增 actions；更新 `syncUploadedFiles`；persist version +1 + migrate |
| `frontend/src/services/excelApi.ts` | `uploadCategoryListings` 加 `storeType: 'pz' | 'ep'` 参数 |
| `frontend/src/components/ExcelUpload/FileUploader.tsx` | EU 国家 category 区拆成 PZ/EP 两块；UK 保持单一区域 |
| `frontend/src/components/ExcelProcess/ProcessButton.tsx` | `category_files` 合并两数组；更新计数显示 |

---

## Task 1: 后端模型 — 更新 UploadedFilesResponse

**Files:**
- Modify: `backend/app/models/excel.py:81-86`

- [ ] **Step 1: 修改 UploadedFilesResponse**

将 `category_listings: list[str]` 替换为两个分区字段：

```python
class UploadedFilesResponse(BaseModel):
    """已上传文件列表。"""

    all_listings: list[str]
    pz_category_listings: list[str]
    ep_category_listings: list[str]
```

- [ ] **Step 2: 验证后端启动无报错**

```bash
cd /Users/melodylu/PycharmProjects/Bu5_ama_ep/backend
python -c "from app.models.excel import UploadedFilesResponse; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/excel.py
git commit -m "feat(backend): split UploadedFilesResponse into pz/ep category listings"
```

---

## Task 2: 后端 API — store_type 参数 + 分区 cleanup + /files 分区返回

**Files:**
- Modify: `backend/app/api/excel.py:367-393`

- [ ] **Step 1: 更新 upload_category 接口**

将 `upload_category` 函数替换为：

```python
@router.post("/upload/category", response_model=UploadResponse)
async def upload_category(
    file: UploadFile = File(...),
    country: str = Form(...),
    store_type: str = Form(...),
) -> UploadResponse:
    """上传 category 文件。store_type 必须为 'pz' 或 'ep'。"""
    if store_type not in ("pz", "ep"):
        raise HTTPException(status_code=422, detail="store_type 必须为 'pz' 或 'ep'")
    resolved_country = _resolve_country(country)
    original_name = _safe_filename(file.filename or "")
    prefix = f"category_{store_type}"
    destination = _create_upload_path(resolved_country, prefix, original_name)
    await _save_upload(
        upload=file,
        destination=destination,
        allowed_extensions=CATEGORY_EXTENSIONS,
        file_label="category 文件",
    )
    _cleanup_old_uploads(
        resolved_country,
        prefix,
        destination,
        keep_latest_only=False,
    )
    return UploadResponse(success=True, filename=destination.name)
```

- [ ] **Step 2: 更新 get_uploaded_files 接口**

```python
@router.get("/files", response_model=UploadedFilesResponse)
async def get_uploaded_files(country: CountryEnum = Query(...)) -> UploadedFilesResponse:
    """按国家列出已上传文件。"""
    return UploadedFilesResponse(
        all_listings=_list_uploaded_files(country, "all_listings"),
        pz_category_listings=_list_uploaded_files(country, "category_pz"),
        ep_category_listings=_list_uploaded_files(country, "category_ep"),
    )
```

- [ ] **Step 3: 验证接口可导入**

```bash
cd /Users/melodylu/PycharmProjects/Bu5_ama_ep/backend
python -c "from app.api.excel import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: 验证旧格式文件名的校验仍然通过**

旧格式 `FR_category_pz_20260323050428_0_APPAREL-DRESS.xlsm` 包含子串 `FR_category_`，所以 `_validate_process_files` 中的检查 `if f"{request.country.value}_category_" not in category_path.name` 仍然通过，无需改动。

```bash
python -c "
name = 'FR_category_pz_20260323050428_0_APPAREL-DRESS.xlsm'
country = 'FR'
assert f'{country}_category_' in name, 'FAIL'
print('校验通过 OK')
"
```

Expected: `校验通过 OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/excel.py
git commit -m "feat(backend): add store_type param to category upload, restore scoped cleanup, split /files response"
```

---

## Task 3: 前端类型 — 更新 UploadedFilesResponse

**Files:**
- Modify: `frontend/src/types/api.ts:88-91`

- [ ] **Step 1: 更新接口定义**

```typescript
export interface UploadedFilesResponse {
  all_listings: string[];
  pz_category_listings: string[];
  ep_category_listings: string[];
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/api.ts
git commit -m "feat(frontend): update UploadedFilesResponse type for pz/ep split"
```

---

## Task 4: 前端 countries — 新增 perStoreCategoryCount

**Files:**
- Modify: `frontend/src/constants/countries.ts`

- [ ] **Step 1: 更新 COUNTRIES 数组类型和数据**

```typescript
export const COUNTRIES: Array<{
  code: Country;
  label: string;
  flag: string;
  locale: string;
  categoryReportCount: number;
  perStoreCategoryCount: number;
}> = [
  { code: 'UK', label: 'United Kingdom', flag: '🇬🇧', locale: 'en-GB', categoryReportCount: 3, perStoreCategoryCount: 0 },
  { code: 'FR', label: 'France', flag: '🇫🇷', locale: 'fr-FR', categoryReportCount: 4, perStoreCategoryCount: 2 },
  { code: 'DE', label: 'Germany', flag: '🇩🇪', locale: 'de-DE', categoryReportCount: 4, perStoreCategoryCount: 2 },
  { code: 'IT', label: 'Italy', flag: '🇮🇹', locale: 'it-IT', categoryReportCount: 4, perStoreCategoryCount: 2 },
  { code: 'ES', label: 'Spain', flag: '🇪🇸', locale: 'es-ES', categoryReportCount: 4, perStoreCategoryCount: 2 },
];
```

`perStoreCategoryCount: 0` 表示 UK 不分区，使用单一区域；`2` 表示每个店铺需要 2 张文件。

- [ ] **Step 2: Commit**

```bash
git add frontend/src/constants/countries.ts
git commit -m "feat(frontend): add perStoreCategoryCount to country metadata"
```

---

## Task 5: 前端 Store — 拆分 categoryFiles

**Files:**
- Modify: `frontend/src/store/useUploadStore.ts`

这是最大的改动，需要完整替换 store 文件。

- [ ] **Step 1: 更新 CountryUploadState 接口**

将 `categoryFiles: string[]` 替换为：
```typescript
pzCategoryFiles: string[];
epCategoryFiles: string[];
```

完整的 `CountryUploadState`：
```typescript
interface CountryUploadState {
  allListingsFiles: string[];
  pzCategoryFiles: string[];
  epCategoryFiles: string[];
  analysisResult: AnalysisResult | null;
  selectedPrefixes: string[];
}
```

- [ ] **Step 2: 更新 createEmptyCountryState**

```typescript
const createEmptyCountryState = (): CountryUploadState => ({
  allListingsFiles: [],
  pzCategoryFiles: [],
  epCategoryFiles: [],
  analysisResult: null,
  selectedPrefixes: [],
});
```

- [ ] **Step 3: 更新 UploadStore 接口**

移除旧的 category actions，新增 pz/ep 专用 actions：

```typescript
interface UploadStore {
  filesByCountry: Record<string, CountryUploadState>;
  getAllListingsFiles: (country: string) => string[];
  getPzCategoryFiles: (country: string) => string[];
  getEpCategoryFiles: (country: string) => string[];
  getAnalysisResult: (country: string) => AnalysisResult | null;
  getSelectedPrefixes: (country: string) => string[];
  addAllListingsFile: (country: string, filename: string) => void;
  removeAllListingsFile: (country: string, filename: string) => void;
  addPzCategoryFile: (country: string, filename: string) => void;
  removePzCategoryFile: (country: string, filename: string) => void;
  addEpCategoryFile: (country: string, filename: string) => void;
  removeEpCategoryFile: (country: string, filename: string) => void;
  setAnalysisResult: (country: string, result: AnalysisResult | null) => void;
  setSelectedPrefixes: (country: string, prefixes: string[]) => void;
  syncUploadedFiles: (country: string, files: UploadedFilesResponse) => FileSyncResult;
  clearCountryFiles: (country: string) => void;
}
```

- [ ] **Step 4: 实现所有新 actions（完整替换文件）**

完整文件内容：

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AnalysisResult, UploadedFilesResponse } from '../types/api';

interface CountryUploadState {
  allListingsFiles: string[];
  pzCategoryFiles: string[];
  epCategoryFiles: string[];
  analysisResult: AnalysisResult | null;
  selectedPrefixes: string[];
}

interface FileSyncResult {
  allListingsMissing: boolean;
  allListingsChanged: boolean;
  missingCategoryFiles: string[];
}

const createEmptyCountryState = (): CountryUploadState => ({
  allListingsFiles: [],
  pzCategoryFiles: [],
  epCategoryFiles: [],
  analysisResult: null,
  selectedPrefixes: [],
});

interface UploadStore {
  filesByCountry: Record<string, CountryUploadState>;
  getAllListingsFiles: (country: string) => string[];
  getPzCategoryFiles: (country: string) => string[];
  getEpCategoryFiles: (country: string) => string[];
  getAnalysisResult: (country: string) => AnalysisResult | null;
  getSelectedPrefixes: (country: string) => string[];
  addAllListingsFile: (country: string, filename: string) => void;
  removeAllListingsFile: (country: string, filename: string) => void;
  addPzCategoryFile: (country: string, filename: string) => void;
  removePzCategoryFile: (country: string, filename: string) => void;
  addEpCategoryFile: (country: string, filename: string) => void;
  removeEpCategoryFile: (country: string, filename: string) => void;
  setAnalysisResult: (country: string, result: AnalysisResult | null) => void;
  setSelectedPrefixes: (country: string, prefixes: string[]) => void;
  syncUploadedFiles: (country: string, files: UploadedFilesResponse) => FileSyncResult;
  clearCountryFiles: (country: string) => void;
}

const dedupeFilenames = (filenames: string[]) =>
  Array.from(
    new Set(
      filenames
        .map((filename) => filename.trim())
        .filter(Boolean)
    )
  );

export const useUploadStore = create<UploadStore>()(
  persist(
    (set, get) => ({
      filesByCountry: {},
      getAllListingsFiles: (country) =>
        get().filesByCountry[country]?.allListingsFiles ?? [],
      getPzCategoryFiles: (country) =>
        get().filesByCountry[country]?.pzCategoryFiles ?? [],
      getEpCategoryFiles: (country) =>
        get().filesByCountry[country]?.epCategoryFiles ?? [],
      getAnalysisResult: (country) =>
        get().filesByCountry[country]?.analysisResult ?? null,
      getSelectedPrefixes: (country) =>
        get().filesByCountry[country]?.selectedPrefixes ?? [],
      addAllListingsFile: (country, filename) =>
        set((state) => {
          const countryState = state.filesByCountry[country] ?? createEmptyCountryState();
          return {
            filesByCountry: {
              ...state.filesByCountry,
              [country]: {
                ...countryState,
                allListingsFiles: dedupeFilenames([...countryState.allListingsFiles, filename]),
              },
            },
          };
        }),
      removeAllListingsFile: (country, filename) =>
        set((state) => {
          const countryState = state.filesByCountry[country] ?? createEmptyCountryState();
          const nextAllListingsFiles = countryState.allListingsFiles.filter((file) => file !== filename);
          const analysisMatchesDeletedFile = countryState.analysisResult?.filename === filename;
          return {
            filesByCountry: {
              ...state.filesByCountry,
              [country]: {
                ...countryState,
                allListingsFiles: nextAllListingsFiles,
                analysisResult: analysisMatchesDeletedFile ? null : countryState.analysisResult,
                selectedPrefixes: analysisMatchesDeletedFile ? [] : countryState.selectedPrefixes,
              },
            },
          };
        }),
      addPzCategoryFile: (country, filename) =>
        set((state) => {
          const countryState = state.filesByCountry[country] ?? createEmptyCountryState();
          return {
            filesByCountry: {
              ...state.filesByCountry,
              [country]: {
                ...countryState,
                pzCategoryFiles: countryState.pzCategoryFiles.includes(filename)
                  ? countryState.pzCategoryFiles
                  : [...countryState.pzCategoryFiles, filename],
              },
            },
          };
        }),
      removePzCategoryFile: (country, filename) =>
        set((state) => {
          const countryState = state.filesByCountry[country] ?? createEmptyCountryState();
          return {
            filesByCountry: {
              ...state.filesByCountry,
              [country]: {
                ...countryState,
                pzCategoryFiles: countryState.pzCategoryFiles.filter((file) => file !== filename),
              },
            },
          };
        }),
      addEpCategoryFile: (country, filename) =>
        set((state) => {
          const countryState = state.filesByCountry[country] ?? createEmptyCountryState();
          return {
            filesByCountry: {
              ...state.filesByCountry,
              [country]: {
                ...countryState,
                epCategoryFiles: countryState.epCategoryFiles.includes(filename)
                  ? countryState.epCategoryFiles
                  : [...countryState.epCategoryFiles, filename],
              },
            },
          };
        }),
      removeEpCategoryFile: (country, filename) =>
        set((state) => {
          const countryState = state.filesByCountry[country] ?? createEmptyCountryState();
          return {
            filesByCountry: {
              ...state.filesByCountry,
              [country]: {
                ...countryState,
                epCategoryFiles: countryState.epCategoryFiles.filter((file) => file !== filename),
              },
            },
          };
        }),
      setAnalysisResult: (country, analysisResult) =>
        set((state) => ({
          filesByCountry: {
            ...state.filesByCountry,
            [country]: {
              ...createEmptyCountryState(),
              ...state.filesByCountry[country],
              analysisResult,
            },
          },
        })),
      setSelectedPrefixes: (country, selectedPrefixes) =>
        set((state) => ({
          filesByCountry: {
            ...state.filesByCountry,
            [country]: {
              ...createEmptyCountryState(),
              ...state.filesByCountry[country],
              selectedPrefixes,
            },
          },
        })),
      syncUploadedFiles: (country, files) => {
        const countryState = get().filesByCountry[country] ?? createEmptyCountryState();
        const currentAllListingsFiles = dedupeFilenames(countryState.allListingsFiles);
        const nextAllListingsFiles = dedupeFilenames(files.all_listings);
        const nextPzCategoryFiles = dedupeFilenames(files.pz_category_listings);
        const nextEpCategoryFiles = dedupeFilenames(files.ep_category_listings);

        const allListingsMissing =
          currentAllListingsFiles.length > 0 &&
          currentAllListingsFiles.some((filename) => !nextAllListingsFiles.includes(filename));
        const allListingsChanged =
          currentAllListingsFiles.length > 0 &&
          (
            currentAllListingsFiles.length !== nextAllListingsFiles.length ||
            currentAllListingsFiles.some((filename, index) => filename !== nextAllListingsFiles[index])
          );

        const allCurrentCategory = [
          ...countryState.pzCategoryFiles,
          ...countryState.epCategoryFiles,
        ];
        const allNextCategory = [...nextPzCategoryFiles, ...nextEpCategoryFiles];
        const missingCategoryFiles = allCurrentCategory.filter(
          (filename) => !allNextCategory.includes(filename)
        );

        const analysisFilename = countryState.analysisResult?.filename?.trim();
        const preserveAnalysis =
          Boolean(analysisFilename) && nextAllListingsFiles.includes(analysisFilename ?? '');

        set((state) => ({
          filesByCountry: {
            ...state.filesByCountry,
            [country]: {
              ...createEmptyCountryState(),
              ...countryState,
              allListingsFiles: nextAllListingsFiles,
              pzCategoryFiles: nextPzCategoryFiles,
              epCategoryFiles: nextEpCategoryFiles,
              analysisResult: preserveAnalysis ? countryState.analysisResult : null,
              selectedPrefixes: preserveAnalysis ? countryState.selectedPrefixes : [],
            },
          },
        }));

        return {
          allListingsMissing,
          allListingsChanged,
          missingCategoryFiles,
        };
      },
      clearCountryFiles: (country) =>
        set((state) => ({
          filesByCountry: {
            ...state.filesByCountry,
            [country]: createEmptyCountryState(),
          },
        })),
    }),
    {
      name: 'amzeu-upload-store',
      version: 2,
      migrate: (persistedState: unknown, version: number) => {
        if (version === 0 || version === 1) {
          // 旧版有 categoryFiles 字段，迁移时清空（旧格式文件名不会在新 UI 中显示）
          const state = persistedState as { filesByCountry?: Record<string, unknown> };
          if (state.filesByCountry) {
            for (const country of Object.keys(state.filesByCountry)) {
              const countryState = state.filesByCountry[country] as Record<string, unknown>;
              delete countryState['categoryFiles'];
              countryState['pzCategoryFiles'] = [];
              countryState['epCategoryFiles'] = [];
            }
          }
        }
        return persistedState as UploadStore;
      },
    }
  )
);
```

- [ ] **Step 5: 验证 TypeScript 编译**

```bash
cd /Users/melodylu/PycharmProjects/Bu5_ama_ep/frontend
npx tsc --noEmit 2>&1 | head -30
```

Expected: 0 errors（或只有其他文件的已知错误）

- [ ] **Step 6: Commit**

```bash
git add frontend/src/store/useUploadStore.ts
git commit -m "feat(frontend): split categoryFiles into pzCategoryFiles/epCategoryFiles, bump persist version"
```

---

## Task 6: 前端 Service — excelApi 加 storeType

**Files:**
- Modify: `frontend/src/services/excelApi.ts:37-52`

- [ ] **Step 1: 更新 uploadCategoryListings 方法**

```typescript
async uploadCategoryListings(
  file: File,
  country: Country,
  storeType: 'pz' | 'ep'
): Promise<{ success: boolean; filename: string }> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('country', country);
  formData.append('store_type', storeType);

  const { data } = await apiClient.post<{ success: boolean; filename: string }>(
    '/api/excel/upload/category',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return data;
},
```

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd /Users/melodylu/PycharmProjects/Bu5_ama_ep/frontend
npx tsc --noEmit 2>&1 | head -30
```

Expected: 编译器会报 FileUploader.tsx 调用处参数不足——这是预期的，下一个 task 修复。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/excelApi.ts
git commit -m "feat(frontend): add storeType param to uploadCategoryListings"
```

---

## Task 7: FileUploader — PZ/EP 分区 UI

**Files:**
- Modify: `frontend/src/components/ExcelUpload/FileUploader.tsx`

这是最复杂的 UI 改动。EU 国家（`perStoreCategoryCount > 0`）渲染两个独立子区域，UK（`perStoreCategoryCount === 0`）只渲染单一 PZ 区域。

- [ ] **Step 1: 更新 store 引用**

将 store 解构改为使用新的 pz/ep actions：

```typescript
const {
  getAllListingsFiles,
  getPzCategoryFiles,
  getEpCategoryFiles,
  getAnalysisResult,
  getSelectedPrefixes,
  addAllListingsFile,
  removeAllListingsFile,
  addPzCategoryFile,
  removePzCategoryFile,
  addEpCategoryFile,
  removeEpCategoryFile,
  setAnalysisResult,
  setSelectedPrefixes,
  syncUploadedFiles,
} = useUploadStore();
const allListingsFiles = getAllListingsFiles(country);
const pzCategoryFiles = getPzCategoryFiles(country);
const epCategoryFiles = getEpCategoryFiles(country);
```

- [ ] **Step 2: 更新 state 变量**

将 `isUploadingCategory` + `categoryInputRef` 替换为两套独立 state：

```typescript
const [isUploadingPzCategory, setIsUploadingPzCategory] = useState(false);
const [isUploadingEpCategory, setIsUploadingEpCategory] = useState(false);
const [deletingPzCategoryFiles, setDeletingPzCategoryFiles] = useState<Set<string>>(new Set());
const [deletingEpCategoryFiles, setDeletingEpCategoryFiles] = useState<Set<string>>(new Set());
const pzCategoryInputRef = useRef<HTMLInputElement | null>(null);
const epCategoryInputRef = useRef<HTMLInputElement | null>(null);
```

- [ ] **Step 3: 实现 upload/delete handlers**

PZ handler：
```typescript
const handlePzCategoryUpload = async (event: ChangeEvent<HTMLInputElement>) => {
  const file = event.target.files?.[0];
  if (!file) return;
  setIsUploadingPzCategory(true);
  try {
    const result = await excelApi.uploadCategoryListings(file, country, 'pz');
    addPzCategoryFile(country, result.filename ?? file.name);
    setSyncMessages([]);
    syncSignatureRef.current[country] = '';
    void queryClient.invalidateQueries({ queryKey: ['excel-uploaded-files', country] });
    toast.success('PZ Category 文件已上传');
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '上传失败');
  } finally {
    setIsUploadingPzCategory(false);
    event.target.value = '';
  }
};

const handlePzCategoryFileDelete = async (filename: string) => {
  if (deletingPzCategoryFiles.has(filename)) return;
  setDeletingPzCategoryFiles((current) => new Set(current).add(filename));
  try {
    await excelApi.deleteUploadedFile(filename);
    removePzCategoryFile(country, filename);
    syncSignatureRef.current[country] = '';
    void queryClient.invalidateQueries({ queryKey: ['excel-uploaded-files', country] });
    toast.success('文件已删除');
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '删除失败');
  } finally {
    setDeletingPzCategoryFiles((current) => {
      const next = new Set(current);
      next.delete(filename);
      return next;
    });
  }
};
```

EP handler（与 PZ 结构相同，替换 pz→ep）：
```typescript
const handleEpCategoryUpload = async (event: ChangeEvent<HTMLInputElement>) => {
  const file = event.target.files?.[0];
  if (!file) return;
  setIsUploadingEpCategory(true);
  try {
    const result = await excelApi.uploadCategoryListings(file, country, 'ep');
    addEpCategoryFile(country, result.filename ?? file.name);
    setSyncMessages([]);
    syncSignatureRef.current[country] = '';
    void queryClient.invalidateQueries({ queryKey: ['excel-uploaded-files', country] });
    toast.success('EP Category 文件已上传');
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '上传失败');
  } finally {
    setIsUploadingEpCategory(false);
    event.target.value = '';
  }
};

const handleEpCategoryFileDelete = async (filename: string) => {
  if (deletingEpCategoryFiles.has(filename)) return;
  setDeletingEpCategoryFiles((current) => new Set(current).add(filename));
  try {
    await excelApi.deleteUploadedFile(filename);
    removeEpCategoryFile(country, filename);
    syncSignatureRef.current[country] = '';
    void queryClient.invalidateQueries({ queryKey: ['excel-uploaded-files', country] });
    toast.success('文件已删除');
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '删除失败');
  } finally {
    setDeletingEpCategoryFiles((current) => {
      const next = new Set(current);
      next.delete(filename);
      return next;
    });
  }
};
```

- [ ] **Step 4: 实现通用 CategorySubSection 渲染函数**

在组件内定义一个辅助函数，渲染单个店铺的 category 上传区域：

```typescript
const renderCategorySubSection = ({
  label,
  files,
  deletingFiles,
  isUploading,
  inputRef,
  onUpload,
  onDelete,
  perStoreCount,
}: {
  label: string;
  files: string[];
  deletingFiles: Set<string>;
  isUploading: boolean;
  inputRef: React.RefObject<HTMLInputElement | null>;
  onUpload: (event: ChangeEvent<HTMLInputElement>) => void;
  onDelete: (filename: string) => void;
  perStoreCount: number;
}) => {
  const remaining = Math.max(perStoreCount - files.length, 0);
  const uploadLabel = isUploading
    ? '上传中...'
    : remaining > 0
    ? `还需上传 ${remaining} 张`
    : '已满足可继续上传';

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-ink">🏪 {label}</div>
          <div className="mt-0.5 text-xs text-steel">需 {perStoreCount} 张</div>
        </div>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={isUploading}
          className="rounded-full bg-signal px-3 py-1.5 text-xs font-semibold text-white transition hover:opacity-90 disabled:opacity-60"
        >
          {uploadLabel}
        </button>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.xlsm,.xls"
        className="hidden"
        onChange={onUpload}
      />
      <div className="mt-3 space-y-2">
        {files.length === 0 ? (
          <div className="text-xs text-steel">尚未上传文件。</div>
        ) : (
          files.map((filename) => {
            const isDeleting = deletingFiles.has(filename);
            return (
              <div
                key={filename}
                className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50 px-3 py-2 text-xs"
              >
                <span className="font-medium text-ink truncate max-w-[70%]">{filename}</span>
                <button
                  type="button"
                  onClick={() => void onDelete(filename)}
                  disabled={isDeleting}
                  className="text-xs font-semibold text-slate-400 transition hover:text-red-500 disabled:cursor-not-allowed disabled:opacity-60 shrink-0"
                >
                  {isDeleting ? '删除中...' : '删除'}
                </button>
              </div>
            );
          })
        )}
      </div>
      {files.length >= perStoreCount && perStoreCount > 0 && (
        <div className="mt-2 text-center">
          <span className="inline-block rounded-full bg-emerald-50 px-3 py-0.5 text-xs font-semibold text-emerald-600">
            ✓ 已满足
          </span>
        </div>
      )}
    </div>
  );
};
```

- [ ] **Step 5: 更新 Category 区域的 JSX**

将原来的单一 category 上传区域替换为条件渲染：

```tsx
<div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 p-5">
  <div className="mb-4">
    <div className="text-sm font-bold text-ink">Category Listings Reports</div>
    <div className="mt-1 text-sm text-steel">
      当前国家目标 {countryMeta.categoryReportCount} 张，至少上传 1 张即可处理。
    </div>
  </div>

  {countryMeta.perStoreCategoryCount > 0 ? (
    // EU 国家：PZ + EP 分区
    <div className="grid gap-3 sm:grid-cols-2">
      {renderCategorySubSection({
        label: 'PZ 店铺',
        files: pzCategoryFiles,
        deletingFiles: deletingPzCategoryFiles,
        isUploading: isUploadingPzCategory,
        inputRef: pzCategoryInputRef,
        onUpload: handlePzCategoryUpload,
        onDelete: handlePzCategoryFileDelete,
        perStoreCount: countryMeta.perStoreCategoryCount,
      })}
      {renderCategorySubSection({
        label: 'EP 店铺',
        files: epCategoryFiles,
        deletingFiles: deletingEpCategoryFiles,
        isUploading: isUploadingEpCategory,
        inputRef: epCategoryInputRef,
        onUpload: handleEpCategoryUpload,
        onDelete: handleEpCategoryFileDelete,
        perStoreCount: countryMeta.perStoreCategoryCount,
      })}
    </div>
  ) : (
    // UK：单一 PZ 区域
    <div>
      {renderCategorySubSection({
        label: 'Category 文件',
        files: pzCategoryFiles,
        deletingFiles: deletingPzCategoryFiles,
        isUploading: isUploadingPzCategory,
        inputRef: pzCategoryInputRef,
        onUpload: handlePzCategoryUpload,
        onDelete: handlePzCategoryFileDelete,
        perStoreCount: countryMeta.categoryReportCount,
      })}
    </div>
  )}
</div>
```

- [ ] **Step 6: 更新 Upload Rules 显示**

将旧的 `categoryListingsFiles` 引用改为合并计数：

```tsx
<li>Category Listings: at least 1 file, target {countryMeta.categoryReportCount} files</li>
```

这行保持不变，只是移除了旧 state 变量的引用。

- [ ] **Step 7: 验证 TypeScript 编译无错误**

```bash
cd /Users/melodylu/PycharmProjects/Bu5_ama_ep/frontend
npx tsc --noEmit 2>&1 | head -30
```

Expected: 0 errors（ProcessButton.tsx 引用 `getCategoryFiles` 还未修改，此时应还有 1 个错误，下一 task 修复）

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/ExcelUpload/FileUploader.tsx
git commit -m "feat(frontend): split category upload into PZ/EP sections for EU countries"
```

---

## Task 8: ProcessButton — 合并两数组 + 更新计数

**Files:**
- Modify: `frontend/src/components/ExcelProcess/ProcessButton.tsx`

- [ ] **Step 1: 更新 store 引用**

将：
```typescript
const { getAllListingsFiles, getCategoryFiles, getSelectedPrefixes } = useUploadStore();
const allListingsFiles = getAllListingsFiles(country);
const categoryListingsFiles = getCategoryFiles(country);
```

替换为：
```typescript
const { getAllListingsFiles, getPzCategoryFiles, getEpCategoryFiles, getSelectedPrefixes } = useUploadStore();
const allListingsFiles = getAllListingsFiles(country);
const pzCategoryFiles = getPzCategoryFiles(country);
const epCategoryFiles = getEpCategoryFiles(country);
const categoryListingsFiles = [...pzCategoryFiles, ...epCategoryFiles];
```

- [ ] **Step 2: 验证其余代码无需改动**

`categoryListingsFiles` 合并后，以下代码无需任何修改：
- `categoryListingsFiles.length < 1` 校验逻辑
- `category_files: categoryListingsFiles` 请求参数
- `Category: {categoryListingsFiles.length}/{countryMeta.categoryReportCount}` 显示

- [ ] **Step 3: 验证 TypeScript 编译无错误**

```bash
cd /Users/melodylu/PycharmProjects/Bu5_ama_ep/frontend
npx tsc --noEmit 2>&1 | head -30
```

Expected: 0 errors

- [ ] **Step 4: 构建前端**

```bash
cd /Users/melodylu/PycharmProjects/Bu5_ama_ep/frontend
npm run build 2>&1 | tail -20
```

Expected: `✓ built in ...`，无错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ExcelProcess/ProcessButton.tsx
git commit -m "feat(frontend): merge pz/ep category files in ProcessButton"
```

---

## Task 9: 端到端验证

- [ ] **Step 1: 启动后端**

```bash
cd /Users/melodylu/PycharmProjects/Bu5_ama_ep
docker compose up --build -d
```

或：
```bash
cd backend && uvicorn app.main:app --reload
```

- [ ] **Step 2: 测试 store_type 校验**

```bash
# 非法 store_type 应返回 422
curl -s -X POST http://localhost:8000/api/excel/upload/category \
  -F "file=@backend/uploads/FR_category_20260323015437_0_APPAREL_HEAD_NECK_COVERING-DRESS.xlsm" \
  -F "country=FR" \
  -F "store_type=invalid" | python3 -m json.tool
```

Expected: `{"detail": "store_type 必须为 'pz' 或 'ep'"}`

- [ ] **Step 3: 测试 PZ 上传**

```bash
curl -s -X POST http://localhost:8000/api/excel/upload/category \
  -F "file=@0_APPAREL_HEAD_NECK_COVERING-DRESS.xlsm" \
  -F "country=FR" \
  -F "store_type=pz" | python3 -m json.tool
```

Expected: `{"success": true, "filename": "FR_category_pz_..._0_APPAREL_HEAD_NECK_COVERING-DRESS.xlsm"}`

- [ ] **Step 4: 测试 EP 上传同名文件**

```bash
curl -s -X POST http://localhost:8000/api/excel/upload/category \
  -F "file=@0_APPAREL_HEAD_NECK_COVERING-DRESS.xlsm" \
  -F "country=FR" \
  -F "store_type=ep" | python3 -m json.tool
```

Expected: `{"success": true, "filename": "FR_category_ep_..._0_APPAREL_HEAD_NECK_COVERING-DRESS.xlsm"}`

- [ ] **Step 5: 验证 /files 接口返回分区数据**

```bash
curl -s "http://localhost:8000/api/excel/files?country=FR" | python3 -m json.tool
```

Expected:
```json
{
  "all_listings": [...],
  "pz_category_listings": ["FR_category_pz_..._0_APPAREL_HEAD_NECK_COVERING-DRESS.xlsm"],
  "ep_category_listings": ["FR_category_ep_..._0_APPAREL_HEAD_NECK_COVERING-DRESS.xlsm"]
}
```

- [ ] **Step 6: 验证前端 UI**

打开浏览器，选择 FR 国家，确认：
- Category 区域显示 **PZ 店铺** 和 **EP 店铺** 两个子区域
- 切换到 UK，Category 区域只显示单一上传区域
- 上传文件后，相应区域文件列表更新
- 删除文件后，文件从列表消失，服务器文件被删除

- [ ] **Step 7: Final commit（如有遗留）**

```bash
git status
# 确认无未提交改动
```
