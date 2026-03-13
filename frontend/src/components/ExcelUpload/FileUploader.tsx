import type { ChangeEvent, KeyboardEvent } from 'react';
import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { getCountryMeta } from '../../constants/countries';
import { excelApi } from '../../services/excelApi';
import { useProcessStore } from '../../store/useProcessStore';
import { useUploadStore } from '../../store/useUploadStore';

const buildSyncMessages = ({
  allListingsMissing,
  allListingsChanged,
  missingCategoryFiles,
}: {
  allListingsMissing: boolean;
  allListingsChanged: boolean;
  missingCategoryFiles: string[];
}) => {
  const messages: string[] = [];

  if (allListingsMissing) {
    messages.push('之前选择的 All Listings 文件已不存在，已按服务器状态清空前缀分析，请重新上传。');
  } else if (allListingsChanged) {
    messages.push('检测到服务器上的 All Listings 已更新，前缀分析已清空，请重新上传或重新确认。');
  }

  if (missingCategoryFiles.length > 0) {
    messages.push(`以下 Category 文件已不存在，已从当前表单移除：${missingCategoryFiles.join('，')}`);
  }

  return messages;
};

export function FileUploader() {
  const country = useProcessStore((state) => state.country);
  const countryMeta = getCountryMeta(country);
  const queryClient = useQueryClient();
  const {
    getAllListingsFile,
    getCategoryFiles,
    getAnalysisResult,
    getSelectedPrefixes,
    setAllListingsFile,
    addCategoryFile,
    removeCategoryFile,
    setAnalysisResult,
    setSelectedPrefixes,
    syncUploadedFiles,
  } = useUploadStore();
  const allListingsFile = getAllListingsFile(country);
  const categoryListingsFiles = getCategoryFiles(country);
  const analysisResult = getAnalysisResult(country);
  const selectedPrefixes = getSelectedPrefixes(country);

  const [isUploadingAll, setIsUploadingAll] = useState(false);
  const [isUploadingCategory, setIsUploadingCategory] = useState(false);
  const [deletingCategoryFiles, setDeletingCategoryFiles] = useState<Set<string>>(new Set());
  const [manualPrefix, setManualPrefix] = useState('');
  const [syncMessages, setSyncMessages] = useState<string[]>([]);
  const syncSignatureRef = useRef<Record<string, string>>({});

  const uploadedFilesQuery = useQuery({
    queryKey: ['excel-uploaded-files', country],
    queryFn: () => excelApi.getUploadedFiles(country),
  });

  useEffect(() => {
    setSyncMessages([]);
  }, [country]);

  useEffect(() => {
    if (!uploadedFilesQuery.data) {
      return;
    }

    const signature = JSON.stringify(uploadedFilesQuery.data);
    if (syncSignatureRef.current[country] === signature) {
      return;
    }
    syncSignatureRef.current[country] = signature;

    const syncResult = syncUploadedFiles(country, uploadedFilesQuery.data);
    const nextMessages = buildSyncMessages(syncResult);
    setSyncMessages(nextMessages);

    nextMessages.forEach((message) => {
      toast.error(message, { duration: 5000 });
    });
  }, [country, syncUploadedFiles, uploadedFilesQuery.data]);

  const handleAddManualPrefix = () => {
    const normalized = manualPrefix.trim().toUpperCase();
    if (!normalized) return;
    if (!selectedPrefixes.includes(normalized)) {
      setSelectedPrefixes(country, [...selectedPrefixes, normalized]);
    }
    setManualPrefix('');
  };

  const handleManualPrefixKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') handleAddManualPrefix();
  };
  const allInputRef = useRef<HTMLInputElement | null>(null);
  const categoryInputRef = useRef<HTMLInputElement | null>(null);

  const remainingCategoryCount = Math.max(
    countryMeta.categoryReportCount - categoryListingsFiles.length,
    0
  );

  const handleAllListingsUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploadingAll(true);
    try {
      if (allListingsFile) {
        try {
          await excelApi.deleteUploadedFile(allListingsFile);
        } catch {
          // Ignore cleanup failures before replacing the file.
        }
      }

      const result = await excelApi.uploadAllListings(file, country);
      setAllListingsFile(country, result.filename ?? file.name);
      setAnalysisResult(country, {
        filename: result.filename ?? file.name,
        success: result.success,
        total_skus: result.total_skus,
        prefixes: result.prefixes,
        suffixes: result.suffixes,
        color_distribution: result.color_distribution,
      });
      setSelectedPrefixes(country, []);
      setSyncMessages([]);
      syncSignatureRef.current[country] = '';
      void queryClient.invalidateQueries({ queryKey: ['excel-uploaded-files', country] });
      toast.success('All Listings Report 已上传');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '上传失败');
    } finally {
      setIsUploadingAll(false);
      event.target.value = '';
    }
  };

  const handleCategoryUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (categoryListingsFiles.length >= countryMeta.categoryReportCount) {
      toast.error(`当前国家最多上传 ${countryMeta.categoryReportCount} 张 Category Listings`);
      event.target.value = '';
      return;
    }

    setIsUploadingCategory(true);
    try {
      const result = await excelApi.uploadCategoryListings(file, country);
      addCategoryFile(country, result.filename ?? file.name);
      setSyncMessages([]);
      syncSignatureRef.current[country] = '';
      void queryClient.invalidateQueries({ queryKey: ['excel-uploaded-files', country] });
      toast.success('Category Listings Report 已上传');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '上传失败');
    } finally {
      setIsUploadingCategory(false);
      event.target.value = '';
    }
  };

  const handleCategoryFileDelete = async (filename: string) => {
    if (deletingCategoryFiles.has(filename)) {
      return;
    }

    setDeletingCategoryFiles((current) => new Set(current).add(filename));
    try {
      await excelApi.deleteUploadedFile(filename);
      removeCategoryFile(country, filename);
      syncSignatureRef.current[country] = '';
      void queryClient.invalidateQueries({ queryKey: ['excel-uploaded-files', country] });
      toast.success('文件已删除');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '删除失败');
    } finally {
      setDeletingCategoryFiles((current) => {
        const next = new Set(current);
        next.delete(filename);
        return next;
      });
    }
  };

  return (
    <section className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
      <div className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-panel">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.32em] text-aurora">Excel Intake</p>
            <h3 className="mt-2 text-xl font-extrabold text-ink">上传源文件</h3>
          </div>
          <div className="rounded-full bg-mist px-3 py-1 text-xs font-semibold text-ink">
            {country} / {countryMeta.categoryReportCount} category reports
          </div>
        </div>

        <div className="mt-6 grid gap-4">
          <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 p-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="text-sm font-bold text-ink">All Listings Report (Custom)</div>
                <div className="mt-1 text-sm text-steel">每个国家仅需 1 张，上传后将返回可选前缀与颜色分布。</div>
              </div>
              <button
                type="button"
                onClick={() => allInputRef.current?.click()}
                disabled={isUploadingAll}
                className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60"
              >
                {isUploadingAll ? '上传中...' : allListingsFile ? '替换文件' : '选择文件'}
              </button>
            </div>
            <input
              ref={allInputRef}
              type="file"
              accept=".txt,.tsv,.csv"
              className="hidden"
              onChange={handleAllListingsUpload}
            />
            <div className="mt-3 text-sm text-steel">
              当前文件：<span className="font-semibold text-ink">{allListingsFile ?? '未上传'}</span>
            </div>
          </div>

          <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 p-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="text-sm font-bold text-ink">Category Listings Reports</div>
                <div className="mt-1 text-sm text-steel">
                  当前国家需要 {countryMeta.categoryReportCount} 张，文件名前缀不限制，还需上传 {remainingCategoryCount} 张。
                </div>
              </div>
              <button
                type="button"
                onClick={() => categoryInputRef.current?.click()}
                disabled={isUploadingCategory || remainingCategoryCount === 0}
                className="rounded-full bg-signal px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-60"
              >
                {isUploadingCategory ? '上传中...' : remainingCategoryCount === 0 ? '已满足数量' : '继续上传'}
              </button>
            </div>
            <input
              ref={categoryInputRef}
              type="file"
              accept=".xlsx,.xlsm,.xls"
              className="hidden"
              onChange={handleCategoryUpload}
            />

            <div className="mt-4 space-y-2">
              {categoryListingsFiles.length === 0 ? (
                <div className="text-sm text-steel">尚未上传 Category Listings Reports。</div>
              ) : (
                categoryListingsFiles.map((filename) => {
                  const isDeleting = deletingCategoryFiles.has(filename);
                  return (
                    <div
                      key={filename}
                      className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm"
                    >
                      <span className="font-medium text-ink">{filename}</span>
                      <button
                        type="button"
                        onClick={() => void handleCategoryFileDelete(filename)}
                        disabled={isDeleting}
                        className="text-sm font-semibold text-slate-500 transition hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {isDeleting ? '删除中...' : '删除'}
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {uploadedFilesQuery.isFetching ? (
          <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-steel">
            正在同步服务器上的已上传文件列表...
          </div>
        ) : null}
        {uploadedFilesQuery.isError ? (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            无法同步服务器文件列表，当前页面可能仍显示旧的本地缓存文件名。
          </div>
        ) : null}
        {syncMessages.length > 0 ? (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {syncMessages.map((message) => (
              <div key={message}>{message}</div>
            ))}
          </div>
        ) : null}
      </div>

      <div className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-panel">
        <p className="text-xs font-bold uppercase tracking-[0.32em] text-pine">Analysis</p>
        <h3 className="mt-2 text-xl font-extrabold text-ink">前缀预检</h3>
        <p className="mt-2 text-sm text-steel">上传 All Listings 后可在这里快速锁定本次参与处理的产品前缀。</p>

        {analysisResult && analysisResult.prefixes.length > 0 && (
          <div className="mt-4 flex gap-2">
            <button
              type="button"
              onClick={() => setSelectedPrefixes(country, analysisResult.prefixes)}
              className="rounded-full border border-slate-300 px-3 py-1 text-xs font-semibold text-steel hover:border-ink hover:text-ink transition"
            >
              全选
            </button>
            <button
              type="button"
              onClick={() => setSelectedPrefixes(country, [])}
              className="rounded-full border border-slate-300 px-3 py-1 text-xs font-semibold text-steel hover:border-red-400 hover:text-red-500 transition"
            >
              清除
            </button>
            <span className="text-xs text-steel self-center">{selectedPrefixes.length} / {analysisResult.prefixes.length} 已选</span>
          </div>
        )}
        <div className="mt-3 flex flex-wrap gap-2">
          {analysisResult && analysisResult.prefixes.length > 0 ? (
            analysisResult.prefixes.map((prefix) => {
              const active = selectedPrefixes.includes(prefix);
              return (
              <button
                key={prefix}
                type="button"
                onClick={() =>
                  setSelectedPrefixes(
                    country,
                    active
                      ? selectedPrefixes.filter((item) => item !== prefix)
                      : [...selectedPrefixes, prefix]
                  )
                }
                className={[
                  'rounded-full border px-3 py-2 text-sm font-semibold transition',
                  active ? 'border-ink bg-ink text-white' : 'border-slate-300 bg-white text-steel hover:border-ink hover:text-ink',
                ].join(' ')}
              >
                {prefix}
              </button>
              );
            })
          ) : (
            <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-steel">
              先上传 All Listings Report，系统再返回可选前缀。
            </div>
          )}
        </div>

        <div className="mt-4 flex gap-2">
          <input
            value={manualPrefix}
            onChange={(e) => setManualPrefix(e.target.value)}
            onKeyDown={handleManualPrefixKeyDown}
            placeholder="手动输入前缀，如 EP00930"
            className="flex-1 rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm outline-none transition focus:border-aurora"
          />
          <button
            type="button"
            onClick={handleAddManualPrefix}
            className="rounded-full bg-aurora px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
          >
            添加
          </button>
        </div>

        <div className="mt-6 rounded-3xl bg-mist p-4">
          <div className="text-xs font-bold uppercase tracking-[0.24em] text-steel">Upload Rules</div>
          <ul className="mt-3 space-y-2 text-sm text-ink">
            <li>All Listings: 1 file</li>
            <li>Category Listings: {countryMeta.categoryReportCount} files</li>
            <li>EU 文件名自由，不强制固定前缀</li>
          </ul>
        </div>
      </div>
    </section>
  );
}
