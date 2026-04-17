// frontend/src/pages/FollowSell.tsx
import { useState, useEffect, useRef } from 'react';
import { followSellApi, FollowSellJobStatus } from '../services/followSellApi';
import { COUNTRIES } from '../constants/countries';
import { apiClient } from '../lib/axios';

interface UploadedFiles {
 all_listings: string[];
 pz_category_listings: string[];
 ep_category_listings: string[];
}

export default function FollowSell() {
 const [country, setCountry] = useState('UK');
 const [allListingsFiles, setAllListingsFiles] = useState<string[]>([]);
 const [frAllListingsFile, setFrAllListingsFile] = useState('');
 const [categoryFiles, setCategoryFiles] = useState<string[]>([]);
 const [skuText, setSkuText] = useState('');
 const [uploadedFiles, setUploadedFiles] = useState<UploadedFiles>({ all_listings: [], pz_category_listings: [], ep_category_listings: [] });
 const [jobStatus, setJobStatus] = useState<FollowSellJobStatus | null>(null);
 const [isRunning, setIsRunning] = useState(false);
 const [error, setError] = useState('');
 const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

 useEffect(() => {
 apiClient.get<UploadedFiles>('/api/excel/files', { params: { country } })
  .then(r => setUploadedFiles(r.data))
  .catch(() => {}); // silently ignore errors
 }, [country]);

 useEffect(() => () => { if (pollRef.current) clearTimeout(pollRef.current); }, []);

 const countryConfig = COUNTRIES.find(c => c.code === country);
 const requiredCategoryCount = countryConfig?.categoryReportCount ?? 3;

 const poll = (jobId: string) => {
 pollRef.current = setTimeout(async () => {
  try {
  const status = await followSellApi.pollStatus(jobId);
  setJobStatus(status);
  if (status.status === 'running' || status.status === 'pending') {
   poll(jobId);
  } else {
   setIsRunning(false);
  }
  } catch {
  setIsRunning(false);
  }
 }, 1500);
 };

 const handleSubmit = async () => {
 setError('');
 const newSkus = skuText.split('\n').map(s => s.trim()).filter(Boolean);
 if (allListingsFiles.length === 0) { setError('请选择至少一张 All Listings 文件'); return; }
 if (['DE', 'IT', 'ES'].includes(country) && !frAllListingsFile) {
  setError('DE/IT/ES 跟卖需要选择法国 All Listings 文件（用于获取 FR ASIN）');
  return;
 }
 if (categoryFiles.length < 1) {
  setError('请至少选择 1 张 Category 文件'); return;
 }
 if (newSkus.length === 0) { setError('请输入至少一个新款 SKU'); return; }

 setIsRunning(true);
 try {
  const job = await followSellApi.startProcess({
  country,
  all_listings_files: allListingsFiles,
  category_files: categoryFiles,
  new_skus: newSkus,
  fr_all_listings_file: ['DE', 'IT', 'ES'].includes(country) ? frAllListingsFile : undefined,
  });
  setJobStatus(job);
  poll(job.job_id);
 } catch (e: unknown) {
  const err = e as { response?: { data?: { detail?: string } } };
  setError(err?.response?.data?.detail ?? '请求失败');
  setIsRunning(false);
 }
 };

 const toggleCategoryFile = (f: string) => {
 setCategoryFiles(prev =>
  prev.includes(f) ? prev.filter(x => x !== f) : [...prev, f]
 );
 };

 const toggleAllListingsFile = (filename: string) => {
 setAllListingsFiles((prev) =>
  prev.includes(filename) ? prev.filter((item) => item !== filename) : [...prev, filename]
 );
 };

 return (
 <div className="max-w-2xl mx-auto p-6 space-y-6">
  <h1 className="text-2xl font-bold text-gray-800">跟卖上新</h1>

  {/* Step 1: 文件选择 */}
  <section className="bg-white border p-4 space-y-4">
  <h2 className="font-semibold text-gray-700">Step 1：选择数据文件</h2>

  <div>
   <label className="block text-sm text-gray-600 mb-1">国家</label>
   <select
   className="border px-3 py-2 w-full"
   value={country}
   onChange={e => {
    setCountry(e.target.value);
    setAllListingsFiles([]);
    setCategoryFiles([]);
    setFrAllListingsFile('');
   }}
   >
   {COUNTRIES.map(c => (
    <option key={c.code} value={c.code}>{c.flag} {c.label}</option>
   ))}
   </select>
  </div>

  <div>
   <label className="block text-sm text-gray-600 mb-1">
   All Listings Report（可选多张，已选 {allListingsFiles.length} 张）
   </label>
   <div className="space-y-1 max-h-40 overflow-y-auto border p-2">
   {uploadedFiles.all_listings.map(f => (
    <label key={f} className="flex items-center gap-2 cursor-pointer text-sm">
    <input
     type="checkbox"
     checked={allListingsFiles.includes(f)}
     onChange={() => toggleAllListingsFile(f)}
    />
    {f}
    </label>
   ))}
   {uploadedFiles.all_listings.length === 0 && (
    <p className="text-gray-400 text-sm">暂无已上传的 All Listings 文件</p>
   )}
   </div>
  </div>

  {['DE', 'IT', 'ES'].includes(country) && (
   <div>
   <label className="block text-sm text-gray-600 mb-1">
    法国 All Listings Report <span className="text-red-500">*</span>
    <span className="text-xs text-gray-400 ml-1">（DE/IT/ES 跟卖需要 FR ASIN）</span>
   </label>
   <select
    className="border px-3 py-2 w-full"
    value={frAllListingsFile}
    onChange={e => setFrAllListingsFile(e.target.value)}
   >
    <option value="">-- 请选择法国 All Listings --</option>
    {uploadedFiles.all_listings.map(f => (
    <option key={f} value={f}>{f}</option>
    ))}
   </select>
   </div>
  )}

  <div>
   <label className="block text-sm text-gray-600 mb-1">
   Category Listings（至少选 1 张，目标 {requiredCategoryCount} 张，已选 {categoryFiles.length} 张）
   </label>
   <div className="space-y-1 max-h-40 overflow-y-auto border p-2">
   {[...uploadedFiles.pz_category_listings, ...uploadedFiles.ep_category_listings].map(f => (
    <label key={f} className="flex items-center gap-2 cursor-pointer text-sm">
    <input
     type="checkbox"
     checked={categoryFiles.includes(f)}
     onChange={() => toggleCategoryFile(f)}
    />
    {f}
    </label>
   ))}
   {uploadedFiles.pz_category_listings.length === 0 && uploadedFiles.ep_category_listings.length === 0 && (
    <p className="text-gray-400 text-sm">暂无已上传的 Category 文件</p>
   )}
   </div>
  </div>
  </section>

  {/* Step 2: 输入新款 SKU */}
  <section className="bg-white border p-4 space-y-2">
  <h2 className="font-semibold text-gray-700">Step 2：输入新款 SKU</h2>
  <p className="text-xs text-gray-400">每行一个，支持批量粘贴</p>
  <textarea
   className="border px-3 py-2 w-full font-mono text-sm h-32 resize-none"
   placeholder={country === 'UK' ? "EG02088BK04-UK1\nEG02088RD06-UK1\n..." : "EG02088BK04\nEG02088RD06\n..."}
   value={skuText}
   onChange={e => setSkuText(e.target.value)}
  />
  </section>

  {/* Step 3: 生成 */}
  <section className="bg-white border p-4 space-y-3">
  <h2 className="font-semibold text-gray-700">Step 3：生成跟卖表</h2>

  {error && <p className="text-red-500 text-sm">{error}</p>}

  <button
   className="bg-blue-600 text-white px-6 py-2 hover:bg-blue-700 disabled:opacity-50"
   onClick={handleSubmit}
   disabled={isRunning}
  >
   {isRunning ? '处理中...' : '生成跟卖表'}
  </button>

  {jobStatus && (jobStatus.status === 'running' || jobStatus.status === 'pending') && (
   <div className="space-y-1">
   <div className="w-full bg-gray-200 h-2">
    <div
    className="bg-[#0F5BBF] h-2 transition-all"
    style={{ width: `${jobStatus.progress}%` }}
    />
   </div>
   <p className="text-sm text-gray-500">{jobStatus.progress}%</p>
   </div>
  )}

  {jobStatus?.status === 'completed' && jobStatus.result && (
   <div className="space-y-2">
   <p className="text-green-600 font-medium">
    完成！生成 {jobStatus.result.processed_count} 行
   </p>
   <a
    href={followSellApi.getDownloadUrl(jobStatus.result.output_file)}
    className="inline-block bg-green-600 text-white px-4 py-2 hover:bg-green-700 text-sm"
    download
   >
    下载跟卖表
   </a>
   {jobStatus.result.skipped_skus.length > 0 && (
    <details className="text-sm">
    <summary className="text-yellow-600 cursor-pointer">
     跳过 {jobStatus.result.skipped_skus.length} 条（映射/索引未命中）
    </summary>
    <ul className="mt-1 pl-4 text-gray-500">
     {jobStatus.result.skipped_skus.map(s => <li key={s}>{s}</li>)}
    </ul>
    </details>
   )}
   {jobStatus.result.invalid_skus.length > 0 && (
    <details className="text-sm">
    <summary className="text-red-500 cursor-pointer">
     格式不合法 {jobStatus.result.invalid_skus.length} 条
    </summary>
    <ul className="mt-1 pl-4 text-gray-500">
     {jobStatus.result.invalid_skus.map(s => <li key={s}>{s}</li>)}
    </ul>
    </details>
   )}
   {jobStatus.result.no_price_skus.length > 0 && (
    <p className="text-yellow-600 text-sm">
    价格缺失跳过 {jobStatus.result.no_price_skus.length} 条
    </p>
   )}
   {jobStatus.result.identity_skus.length > 0 && (
    <p className="text-yellow-600 text-sm">
    映射表中 {jobStatus.result.identity_skus.join(', ')} 新老款号相同，请核查
    </p>
   )}
   </div>
  )}

  {jobStatus?.status === 'failed' && (
   <p className="text-red-500 text-sm">处理失败：{jobStatus.error}</p>
  )}
  </section>
 </div>
 );
}
