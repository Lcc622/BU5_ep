import { useEffect, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { getCountryMeta } from '../../constants/countries';
import { excelApi } from '../../services/excelApi';
import { useProcessStore } from '../../store/useProcessStore';
import { useUploadStore } from '../../store/useUploadStore';
import { parseDirectSkuText } from './directSku';

const parseColorCodes = (value: string) =>
 value
 .split(/[,，、;\s]+/)
 .map((item) => item.trim().toUpperCase())
 .filter(Boolean);

export function ProcessButton() {
 const country = useProcessStore((state) => state.country);
 const mode = useProcessStore((state) => state.mode);
 const inputMode = useProcessStore((state) => state.inputMode);
 const directSkuText = useProcessStore((state) => state.directSkuText);
 const generatedSkus = useProcessStore((state) => state.generatedSkus);
 const startSize = useProcessStore((state) => state.startSize);
 const endSize = useProcessStore((state) => state.endSize);
 const sizeStep = useProcessStore((state) => state.sizeStep);
 const colorList = useProcessStore((state) => state.colorList);
 const productPrefix = useProcessStore((state) => state.productPrefix);
 const countryMeta = getCountryMeta(country);

 const { getAllListingsFiles, getPzCategoryFiles, getEpCategoryFiles, getSelectedPrefixes } = useUploadStore();
 const allListingsFiles = getAllListingsFiles(country);
 const pzCategoryFiles = getPzCategoryFiles(country);
 const epCategoryFiles = getEpCategoryFiles(country);
 const categoryListingsFiles = [...pzCategoryFiles, ...epCategoryFiles];
 const selectedPrefixes = getSelectedPrefixes(country);
 const [progress, setProgress] = useState(0);
 const [downloadFile, setDownloadFile] = useState<string | null>(null);
 const [jobId, setJobId] = useState<string | null>(null);
 const [jobStatusLabel, setJobStatusLabel] = useState('待执行');

 const selectedColors = parseColorCodes(colorList);
 const directSkuResult = parseDirectSkuText(directSkuText);
 const validationMessages: string[] = [];
 if (allListingsFiles.length === 0) {
 validationMessages.push('请先上传 All Listings 文件');
 }
 if (categoryListingsFiles.length < 1) {
 validationMessages.push('请至少上传 1 份 Category 文件');
 }
 if (inputMode === 'matrix') {
 if (selectedPrefixes.length === 0) {
  validationMessages.push('请至少选择一个前缀');
 }
 if (selectedColors.length === 0) {
  validationMessages.push('请至少选择一个颜色');
 }
 } else {
 if (directSkuResult.uniqueSkus.length === 0) {
  validationMessages.push('请至少输入一个有效 SKU');
 }
 if (directSkuResult.invalidEntries.length > 0) {
  validationMessages.push(`存在 ${directSkuResult.invalidEntries.length} 个格式错误的 SKU`);
 }
 }

 const startMutation = useMutation({
 mutationFn: async () => {
  const request =
  inputMode === 'direct-sku'
   ? {
    country,
    all_listings_files: allListingsFiles,
    category_files: categoryListingsFiles,
    input_mode: 'direct-sku' as const,
    direct_skus: directSkuResult.uniqueSkus,
   }
   : {
    country,
    all_listings_files: allListingsFiles,
    category_files: categoryListingsFiles,
    input_mode: 'matrix' as const,
    selected_prefixes: selectedPrefixes,
    target_colors: selectedColors,
    start_size: startSize,
    end_size: endSize,
    size_step: sizeStep,
    mode,
   };
  const response = await excelApi.startProcess({
  ...request,
  });
  return response;
 },
 onSuccess: (data) => {
  setJobId(data.job_id);
  setJobStatusLabel('任务已创建');
  setProgress(5);
  toast.success(`任务已提交，Job ID: ${data.job_id.slice(0, 8)}`);
 },
 onError: (error) => {
  setJobId(null);
  setProgress(0);
  toast.error(error instanceof Error ? error.message : '处理失败');
 },
 });

 useEffect(() => {
 if (!jobId) {
  return undefined;
 }

 let cancelled = false;

 const pollStatus = async () => {
  try {
  const status = await excelApi.getJobStatus(jobId);
  if (cancelled) {
   return;
  }

  setProgress(Math.max(0, Math.min(status.progress ?? 0, 100)));

  if (status.status === 'completed') {
   setJobStatusLabel('处理完成');
   setDownloadFile(status.result?.output_file ?? null);
   setJobId(null);
   toast.success(`处理完成，生成 ${status.result?.processed_count ?? 0} 条`);
   return;
  }

  if (status.status === 'failed') {
   setJobStatusLabel('处理失败');
   setJobId(null);
   setProgress(0);
   toast.error(status.error || '处理失败');
   return;
  }

  setJobStatusLabel(status.status === 'running' ? '处理中' : '排队中');
  } catch (error) {
  if (cancelled) {
   return;
  }
  setJobId(null);
  setProgress(0);
  setJobStatusLabel('轮询失败');
  toast.error(error instanceof Error ? error.message : '任务状态查询失败');
  }
 };

 pollStatus();
 const timer = window.setInterval(pollStatus, 1500);
 return () => {
  cancelled = true;
  window.clearInterval(timer);
 };
 }, [jobId]);

 const ready = validationMessages.length === 0;
 const isBusy = startMutation.isPending || Boolean(jobId);
 const selectionSummary =
 inputMode === 'direct-sku'
  ? `${directSkuResult.uniqueSkus.length} sku / ${directSkuResult.productCodes.length} product`
  : `${selectedPrefixes.length} prefix / ${selectedColors.length} color`;
 const snapshotTitle = inputMode === 'direct-sku' ? 'Direct SKU Snapshot' : 'SKU Snapshot';
 const snapshotDescription =
 inputMode === 'direct-sku'
  ? `有效 SKU ${directSkuResult.uniqueSkus.length} 条，产品码 ${directSkuResult.productCodes.length} 个，颜色 ${directSkuResult.colorCodes.length} 个`
  : `前缀 ${productPrefix || '未填写'}，尺码 ${startSize} - ${endSize}，步长 ${sizeStep}`;
 const snapshotSubtext =
 inputMode === 'direct-sku'
  ? directSkuResult.invalidEntries.length > 0
  ? `存在 ${directSkuResult.invalidEntries.length} 个格式错误的 SKU`
  : directSkuResult.duplicateCount > 0
   ? `检测到 ${directSkuResult.duplicateCount} 个重复 SKU`
   : 'SKU 文本校验通过'
  : `已预生成 ${generatedSkus.length} 个 SKU`;
 const modeLabel = inputMode === 'direct-sku' ? 'direct-sku' : `matrix · ${mode}`;

 return (
 <section className="rounded-[28px] border border-[#E8EAED] bg-white p-6 shadow-panel">
  <div className="flex flex-wrap items-start justify-between gap-4">
  <div>
   <p className="text-xs font-bold uppercase tracking-[0.32em] text-aurora">Execution</p>
   <h3 className="mt-2 text-xl font-extrabold text-ink">开始处理</h3>
   <p className="mt-2 text-sm text-steel">
   {inputMode === 'direct-sku'
    ? '按国家与 SKU 清单创建异步任务，并每 1.5 秒轮询状态。'
    : '按国家、前缀、颜色和尺码区间创建异步任务，并每 1.5 秒轮询状态。'}
   </p>
  </div>
  <button
   type="button"
   disabled={!ready || isBusy}
   title={!ready ? validationMessages.join('；') : undefined}
   onClick={() => {
   setDownloadFile(null);
   setJobStatusLabel('提交中');
   setProgress(0);
   startMutation.mutate();
   }}
   className=" bg-[#091E40] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[#0D2B52] disabled:opacity-50"
  >
   {isBusy ? '处理中...' : '执行加色加码'}
  </button>
  </div>

  {!ready ? (
  <div className="mt-4 border border-[#E8B84B] bg-[#FFF7E6] px-4 py-3 text-sm text-[#D46B08]">
   {validationMessages.join('；')}
  </div>
  ) : null}

  <div className="mt-5 bg-[#F7F9FA] p-1">
  <div
   className="h-3 bg-[#4D7B75] transition-all duration-500"
   style={{ width: `${progress}%` }}
  />
  </div>

  <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
  <div className=" bg-mist p-4">
   <div className="text-xs font-bold uppercase tracking-[0.18em] text-steel">Country</div>
   <div className="mt-2 text-lg font-bold text-ink">{country}</div>
  </div>
  <div className=" bg-mist p-4">
   <div className="text-xs font-bold uppercase tracking-[0.18em] text-steel">Mode</div>
   <div className="mt-2 text-lg font-bold text-ink">{modeLabel}</div>
  </div>
  <div className=" bg-mist p-4">
   <div className="text-xs font-bold uppercase tracking-[0.18em] text-steel">Status</div>
   <div className="mt-2 text-lg font-bold text-ink">{jobStatusLabel}</div>
  </div>
  <div className=" bg-mist p-4">
   <div className="text-xs font-bold uppercase tracking-[0.18em] text-steel">Selection</div>
   <div className="mt-2 text-lg font-bold text-ink">{selectionSummary}</div>
  </div>
  </div>

  <div className="mt-4 grid gap-3 md:grid-cols-2">
  <div className=" border border-[#E8EAED] bg-[#F7F9FA] p-4">
   <div className="text-xs font-bold uppercase tracking-[0.18em] text-steel">{snapshotTitle}</div>
   <div className="mt-2 text-sm text-ink">{snapshotDescription}</div>
   <div className="mt-1 text-sm text-steel">{snapshotSubtext}</div>
  </div>
  <div className=" border border-[#E8EAED] bg-[#F7F9FA] p-4">
   <div className="text-xs font-bold uppercase tracking-[0.18em] text-steel">Files</div>
   <div className="mt-2 text-sm text-ink">All Listings: {allListingsFiles.length} 份</div>
   <div className="mt-1 text-sm text-steel">
   Category: {categoryListingsFiles.length}/{countryMeta.categoryReportCount}
   </div>
  </div>
  </div>

  {downloadFile ? (
  <a
   href={excelApi.downloadResult(downloadFile)}
   download
   className="mt-5 inline-flex border border-ink px-4 py-2 text-sm font-semibold text-ink transition hover:bg-ink hover:text-white"
  >
   下载结果文件: {downloadFile}
  </a>
  ) : null}
 </section>
 );
}
