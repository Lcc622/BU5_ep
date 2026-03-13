import { useQuery } from '@tanstack/react-query';
import { excelApi } from '../../services/excelApi';

const formatFileSize = (size?: number) => {
  if (typeof size !== 'number' || Number.isNaN(size)) {
    return '--';
  }

  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
};

const formatModifiedTime = (value: string) => {
  const normalizedValue = value.replace(/(\.\d{3})\d+/, '$1');
  // Ensure the string is treated as UTC (append Z if no timezone info)
  const utcValue = /(?:Z|[+\-]\d{2}:?\d{2})$/.test(normalizedValue)
    ? normalizedValue
    : `${normalizedValue}Z`;
  const date = new Date(utcValue);

  if (Number.isNaN(date.getTime())) {
    return '--';
  }

  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Shanghai',
  }).format(date);
};

export function DownloadHistory() {
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['excel-results'],
    queryFn: () => excelApi.getResults(),
  });

  const files = data?.files ?? [];

  return (
    <section className="rounded-[32px] border border-slate-200 bg-white p-6 shadow-panel">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.32em] text-pine">Result Archive</p>
          <h2 className="mt-2 text-2xl font-extrabold text-ink">下载历史</h2>
          <p className="mt-2 text-sm text-steel">查看 `/api/excel/results` 返回的历史结果，并直接下载文件。</p>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold text-ink transition hover:border-ink disabled:opacity-60"
        >
          {isFetching ? '刷新中...' : '刷新列表'}
        </button>
      </div>

      <div className="mt-6 overflow-hidden rounded-3xl border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-[0.18em] text-steel">文件名</th>
              <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-[0.18em] text-steel">大小</th>
              <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-[0.18em] text-steel">修改时间</th>
              <th className="px-4 py-3 text-right text-xs font-bold uppercase tracking-[0.18em] text-steel">下载</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {isLoading ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-sm text-steel">加载历史结果中...</td>
              </tr>
            ) : null}
            {isError ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-sm text-red-600">历史结果加载失败。</td>
              </tr>
            ) : null}
            {!isLoading && !isError && files.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-sm text-steel">暂无历史结果。</td>
              </tr>
            ) : null}
            {!isLoading && !isError
              ? files.map((file) => (
                  <tr key={file.filename}>
                    <td className="px-4 py-4 text-sm font-semibold text-ink">{file.filename}</td>
                    <td className="px-4 py-4 text-sm text-steel">{formatFileSize(file.size)}</td>
                    <td className="px-4 py-4 text-sm text-steel">{formatModifiedTime(file.modified_at)}</td>
                    <td className="px-4 py-4 text-right">
                      <a
                        href={excelApi.downloadResult(file.filename)}
                        download
                        className="inline-flex rounded-full border border-ink px-4 py-2 text-sm font-semibold text-ink transition hover:bg-ink hover:text-white"
                      >
                        下载
                      </a>
                    </td>
                  </tr>
                ))
              : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
