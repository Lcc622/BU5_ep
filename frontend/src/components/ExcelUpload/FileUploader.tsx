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
 messages.push('之前选择的部分 All Listings 文件已不存在，已按服务器状态清空前缀分析，请重新上传。');
 } else if (allListingsChanged) {
 messages.push('检测到服务器上的 All Listings 列表已变化，前缀分析已清空，请重新上传或重新确认。');
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
 const analysisResult = getAnalysisResult(country);
 const selectedPrefixes = getSelectedPrefixes(country);

 const [isUploadingAll, setIsUploadingAll] = useState(false);
 const [isUploadingPzCategory, setIsUploadingPzCategory] = useState(false);
 const [isUploadingEpCategory, setIsUploadingEpCategory] = useState(false);
 const [deletingAllListingsFiles, setDeletingAllListingsFiles] = useState<Set<string>>(new Set());
 const [deletingPzCategoryFiles, setDeletingPzCategoryFiles] = useState<Set<string>>(new Set());
 const [deletingEpCategoryFiles, setDeletingEpCategoryFiles] = useState<Set<string>>(new Set());
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
 const pzCategoryInputRef = useRef<HTMLInputElement | null>(null);
 const epCategoryInputRef = useRef<HTMLInputElement | null>(null);

 const handleAllListingsUpload = async (event: ChangeEvent<HTMLInputElement>) => {
 const file = event.target.files?.[0];
 if (!file) return;

 setIsUploadingAll(true);
 try {
  const result = await excelApi.uploadAllListings(file, country);
  addAllListingsFile(country, result.filename ?? file.name);
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

 const handleAllListingsFileDelete = async (filename: string) => {
 if (deletingAllListingsFiles.has(filename)) {
  return;
 }

 setDeletingAllListingsFiles((current) => new Set(current).add(filename));
 try {
  await excelApi.deleteUploadedFile(filename);
  removeAllListingsFile(country, filename);
  setSyncMessages([]);
  syncSignatureRef.current[country] = '';
  void queryClient.invalidateQueries({ queryKey: ['excel-uploaded-files', country] });
  toast.success('文件已删除');
 } catch (error) {
  toast.error(error instanceof Error ? error.message : '删除失败');
 } finally {
  setDeletingAllListingsFiles((current) => {
  const next = new Set(current);
  next.delete(filename);
  return next;
  });
 }
 };

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
  toast.success('PZ Category Listings Report 已上传');
 } catch (error) {
  toast.error(error instanceof Error ? error.message : '上传失败');
 } finally {
  setIsUploadingPzCategory(false);
  event.target.value = '';
 }
 };

 const handlePzCategoryFileDelete = async (filename: string) => {
 if (deletingPzCategoryFiles.has(filename)) {
  return;
 }

 setDeletingPzCategoryFiles((current) => new Set(current).add(filename));
 try {
  await excelApi.deleteUploadedFile(filename);
  removePzCategoryFile(country, filename);
  setSyncMessages([]);
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
  toast.success('EP Category Listings Report 已上传');
 } catch (error) {
  toast.error(error instanceof Error ? error.message : '上传失败');
 } finally {
  setIsUploadingEpCategory(false);
  event.target.value = '';
 }
 };

 const handleEpCategoryFileDelete = async (filename: string) => {
 if (deletingEpCategoryFiles.has(filename)) {
  return;
 }

 setDeletingEpCategoryFiles((current) => new Set(current).add(filename));
 try {
  await excelApi.deleteUploadedFile(filename);
  removeEpCategoryFile(country, filename);
  setSyncMessages([]);
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

 return (
 <section className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
  <div className="rounded-[28px] border border-[#E8EAED] bg-white p-6 shadow-panel">
  <div className="flex items-start justify-between gap-4">
   <div>
   <p className="text-xs font-bold uppercase tracking-[0.32em] text-aurora">Excel Intake</p>
   <h3 className="mt-2 text-xl font-extrabold text-ink">上传源文件</h3>
   </div>
   <div className=" bg-mist px-3 py-1 text-xs font-semibold text-ink">
   {country} / {countryMeta.categoryReportCount} category reports
   </div>
  </div>

  <div className="mt-6 grid gap-4">
   <div className=" border border-dashed border-[#E8EAED] bg-[#F7F9FA] p-5">
   <div className="flex flex-wrap items-center justify-between gap-4">
    <div>
    <div className="text-sm font-bold text-ink">All Listings Report (Custom)</div>
    <div className="mt-1 text-sm text-steel">
     可上传多张，系统会合并处理；最近上传的文件会刷新可选前缀与颜色分布。
    </div>
    </div>
    <button
    type="button"
    onClick={() => allInputRef.current?.click()}
    disabled={isUploadingAll}
    className=" bg-[#091E40] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#0D2B52] disabled:opacity-60"
    >
    {isUploadingAll ? '上传中...' : '继续上传'}
    </button>
   </div>
   <input
    ref={allInputRef}
    type="file"
    accept=".txt,.tsv,.csv"
    className="hidden"
    onChange={handleAllListingsUpload}
   />
   <div className="mt-4 space-y-2">
    {allListingsFiles.length === 0 ? (
    <div className="text-sm text-steel">尚未上传 All Listings Reports。</div>
    ) : (
    allListingsFiles.map((filename) => {
     const isDeleting = deletingAllListingsFiles.has(filename);
     return (
     <div
      key={filename}
      className="flex items-center justify-between border border-[#E8EAED] bg-white px-4 py-3 text-sm"
     >
      <span className="min-w-0 truncate font-medium text-ink">{filename}</span>
      <button
      type="button"
      onClick={() => void handleAllListingsFileDelete(filename)}
      disabled={isDeleting}
      className="shrink-0 text-sm font-semibold text-[#8C8C8C] transition hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-60"
      >
      {isDeleting ? '删除中...' : '删除'}
      </button>
     </div>
     );
    })
    )}
   </div>
   </div>

   <div className=" border border-dashed border-[#E8EAED] bg-[#F7F9FA] p-5">
   <div>
    <div className="text-sm font-bold text-ink">Category Listings Reports</div>
    <div className="mt-1 text-sm text-steel">
    当前国家目标 {countryMeta.categoryReportCount} 张，至少上传 1 张即可处理，文件名前缀不限制。
    </div>
   </div>

   {countryMeta.perStoreCategoryCount > 0 ? (
    <div className="mt-4 grid gap-4 md:grid-cols-2">
    <div className=" border border-[#E8EAED] bg-white p-4">
     <div className="flex flex-wrap items-center justify-between gap-3">
     <div>
      <div className="text-sm font-bold text-ink">PZ 店铺</div>
      <div className="mt-1 text-xs text-steel">
      每店目标 {countryMeta.perStoreCategoryCount} 张，可继续追加上传。
      </div>
     </div>
     <button
      type="button"
      onClick={() => pzCategoryInputRef.current?.click()}
      disabled={isUploadingPzCategory}
      className=" bg-signal px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-60"
     >
      {isUploadingPzCategory ? '上传中...' : '上传 PZ 文件'}
     </button>
     </div>
     <input
     ref={pzCategoryInputRef}
     type="file"
     accept=".xlsx,.xlsm,.xls"
     className="hidden"
     onChange={handlePzCategoryUpload}
     />
     <div className="mt-4 space-y-2">
     {pzCategoryFiles.length === 0 ? (
      <div className="text-sm text-steel">尚未上传 PZ Category Listings Reports。</div>
     ) : (
      pzCategoryFiles.map((filename) => {
      const isDeleting = deletingPzCategoryFiles.has(filename);
      return (
       <div
       key={filename}
       className="flex items-center justify-between border border-[#E8EAED] bg-[#F7F9FA] px-4 py-3 text-sm"
       >
       <span className="min-w-0 truncate font-medium text-ink">{filename}</span>
       <button
        type="button"
        onClick={() => void handlePzCategoryFileDelete(filename)}
        disabled={isDeleting}
        className="shrink-0 text-sm font-semibold text-[#8C8C8C] transition hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-60"
       >
        {isDeleting ? '删除中...' : '删除'}
       </button>
       </div>
      );
      })
     )}
     </div>
    </div>

    <div className=" border border-[#E8EAED] bg-white p-4">
     <div className="flex flex-wrap items-center justify-between gap-3">
     <div>
      <div className="text-sm font-bold text-ink">EP 店铺</div>
      <div className="mt-1 text-xs text-steel">
      每店目标 {countryMeta.perStoreCategoryCount} 张，可继续追加上传。
      </div>
     </div>
     <button
      type="button"
      onClick={() => epCategoryInputRef.current?.click()}
      disabled={isUploadingEpCategory}
      className=" bg-signal px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-60"
     >
      {isUploadingEpCategory ? '上传中...' : '上传 EP 文件'}
     </button>
     </div>
     <input
     ref={epCategoryInputRef}
     type="file"
     accept=".xlsx,.xlsm,.xls"
     className="hidden"
     onChange={handleEpCategoryUpload}
     />
     <div className="mt-4 space-y-2">
     {epCategoryFiles.length === 0 ? (
      <div className="text-sm text-steel">尚未上传 EP Category Listings Reports。</div>
     ) : (
      epCategoryFiles.map((filename) => {
      const isDeleting = deletingEpCategoryFiles.has(filename);
      return (
       <div
       key={filename}
       className="flex items-center justify-between border border-[#E8EAED] bg-[#F7F9FA] px-4 py-3 text-sm"
       >
       <span className="min-w-0 truncate font-medium text-ink">{filename}</span>
       <button
        type="button"
        onClick={() => void handleEpCategoryFileDelete(filename)}
        disabled={isDeleting}
        className="shrink-0 text-sm font-semibold text-[#8C8C8C] transition hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-60"
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
   ) : (
    <div className="mt-4 border border-[#E8EAED] bg-white p-4">
    <div className="flex flex-wrap items-center justify-between gap-3">
     <div>
     <div className="text-sm font-bold text-ink">Category Listings Reports</div>
     <div className="mt-1 text-xs text-steel">UK 仅使用 PZ 店铺分类文件。</div>
     </div>
     <button
     type="button"
     onClick={() => pzCategoryInputRef.current?.click()}
     disabled={isUploadingPzCategory}
     className=" bg-signal px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-60"
     >
     {isUploadingPzCategory ? '上传中...' : '继续上传'}
     </button>
    </div>
    <input
     ref={pzCategoryInputRef}
     type="file"
     accept=".xlsx,.xlsm,.xls"
     className="hidden"
     onChange={handlePzCategoryUpload}
    />
    <div className="mt-4 space-y-2">
     {pzCategoryFiles.length === 0 ? (
     <div className="text-sm text-steel">尚未上传 Category Listings Reports。</div>
     ) : (
     pzCategoryFiles.map((filename) => {
      const isDeleting = deletingPzCategoryFiles.has(filename);
      return (
      <div
       key={filename}
       className="flex items-center justify-between border border-[#E8EAED] bg-[#F7F9FA] px-4 py-3 text-sm"
      >
       <span className="min-w-0 truncate font-medium text-ink">{filename}</span>
       <button
       type="button"
       onClick={() => void handlePzCategoryFileDelete(filename)}
       disabled={isDeleting}
       className="shrink-0 text-sm font-semibold text-[#8C8C8C] transition hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-60"
       >
       {isDeleting ? '删除中...' : '删除'}
       </button>
      </div>
      );
     })
     )}
    </div>
    </div>
   )}
   </div>
  </div>

  {uploadedFilesQuery.isFetching ? (
   <div className="mt-4 border border-[#E8EAED] bg-[#F7F9FA] px-4 py-3 text-sm text-steel">
   正在同步服务器上的已上传文件列表...
   </div>
  ) : null}
  {uploadedFilesQuery.isError ? (
   <div className="mt-4 border border-[#D14343] bg-[#FEF2F2] px-4 py-3 text-sm text-[#D14343]">
   无法同步服务器文件列表，当前页面可能仍显示旧的本地缓存文件名。
   </div>
  ) : null}
  {syncMessages.length > 0 ? (
   <div className="mt-4 border border-[#E8B84B] bg-[#FFF7E6] px-4 py-3 text-sm text-[#D46B08]">
   {syncMessages.map((message) => (
    <div key={message}>{message}</div>
   ))}
   </div>
  ) : null}
  </div>

  <div className="rounded-[28px] border border-[#E8EAED] bg-white p-6 shadow-panel">
  <p className="text-xs font-bold uppercase tracking-[0.32em] text-pine">Analysis</p>
  <h3 className="mt-2 text-xl font-extrabold text-ink">前缀预检</h3>
  <p className="mt-2 text-sm text-steel">上传 All Listings 后可在这里快速锁定本次参与处理的产品前缀。</p>

  {analysisResult && analysisResult.prefixes.length > 0 && (
   <div className="mt-4 flex gap-2">
   <button
    type="button"
    onClick={() => setSelectedPrefixes(country, analysisResult.prefixes)}
    className=" border border-[#E8EAED] px-3 py-1 text-xs font-semibold text-steel hover:border-ink hover:text-ink transition"
   >
    全选
   </button>
   <button
    type="button"
    onClick={() => setSelectedPrefixes(country, [])}
    className=" border border-[#E8EAED] px-3 py-1 text-xs font-semibold text-steel hover:border-red-400 hover:text-red-500 transition"
   >
    清除
   </button>
   <span className="text-xs text-steel self-center">{selectedPrefixes.length} / {analysisResult.prefixes.length} 已选</span>
   </div>
  )}
  <div className="mt-3 flex max-h-52 flex-wrap gap-2 overflow-y-auto pr-1">
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
     ' border px-3 py-2 text-sm font-semibold transition',
     active ? 'border-ink bg-ink text-white' : 'border-[#E8EAED] bg-white text-steel hover:border-ink hover:text-ink',
    ].join(' ')}
    >
    {prefix}
    </button>
    );
   })
   ) : (
   <div className=" bg-[#F7F9FA] px-4 py-3 text-sm text-steel">
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
   className="flex-1 border border-[#E8EAED] bg-[#F7F9FA] px-4 py-2 text-sm outline-none transition focus:border-aurora"
   />
   <button
   type="button"
   onClick={handleAddManualPrefix}
   className=" bg-aurora px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
   >
   添加
   </button>
  </div>

  <div className="mt-6 bg-mist p-4">
   <div className="text-xs font-bold uppercase tracking-[0.24em] text-steel">Upload Rules</div>
   <ul className="mt-3 space-y-2 text-sm text-ink">
   <li>All Listings: 1 file</li>
   <li>Category Listings: at least 1 file, target {countryMeta.categoryReportCount} files</li>
   <li>EU 文件名自由，不强制固定前缀</li>
   </ul>
  </div>
  </div>
 </section>
 );
}
