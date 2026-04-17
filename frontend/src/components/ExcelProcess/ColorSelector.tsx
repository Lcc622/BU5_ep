import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { mappingApi } from '../../services/mappingApi';
import { useProcessStore } from '../../store/useProcessStore';

const parseSelected = (value: string) =>
  value
    .split(/[,，、;\s]+/)
    .map((item) => item.trim().toUpperCase())
    .filter(Boolean);

export function ColorSelector() {
  const mode = useProcessStore((state) => state.mode);
  const setMode = useProcessStore((state) => state.setMode);
  const colorList = useProcessStore((state) => state.colorList);
  const setColorList = useProcessStore((state) => state.setColorList);
  const [keyword, setKeyword] = useState('');

  const selected = parseSelected(colorList);
  const { data, isLoading, isError } = useQuery({
    queryKey: ['mappings'],
    queryFn: () => mappingApi.getAllMappings(),
  });

  const colorEntries = Object.entries(data ?? {})
    .sort(([leftCode], [rightCode]) => leftCode.localeCompare(rightCode))
    .filter(([code, names]) => {
      if (!keyword.trim()) {
        return true;
      }
      const normalizedKeyword = keyword.trim().toLowerCase();
      return (
        code.toLowerCase().includes(normalizedKeyword) ||
        names.en.toLowerCase().includes(normalizedKeyword) ||
        names.fr.toLowerCase().includes(normalizedKeyword) ||
        names.de.toLowerCase().includes(normalizedKeyword) ||
        names.it.toLowerCase().includes(normalizedKeyword) ||
        names.es.toLowerCase().includes(normalizedKeyword)
      );
    });

  const toggleColor = (code: string) => {
    const next = selected.includes(code)
      ? selected.filter((item) => item !== code)
      : [...selected, code];
    setColorList(next.join(','));
  };

  return (
    <section className="rounded-[28px] border border-[#E8EAED] bg-white p-6 shadow-panel">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.32em] text-pine">Color Strategy</p>
          <h3 className="mt-2 text-xl font-extrabold text-ink">颜色选择与模式切换</h3>
          <p className="mt-2 text-sm text-steel">从颜色映射 API 选择目标颜色，支持关键字搜索与多选同步。</p>
        </div>
        <div className="inline-flex rounded-full bg-[#F7F9FA] p-1">
          {(['add-color', 'add-code'] as const).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setMode(option)}
              className={[
                'rounded-full px-4 py-2 text-sm font-semibold transition',
                mode === option ? 'bg-ink text-white' : 'text-[#8C8C8C] hover:text-ink',
              ].join(' ')}
            >
              {option === 'add-color' ? '加色' : '加码'}
            </button>
          ))}
        </div>
      </div>

      <label className="mt-5 block">
        <span className="mb-2 block text-sm font-semibold text-ink">搜索颜色代码或名称</span>
        <input
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          placeholder="例如 BK、black、navy"
          className="w-full  border border-[#E8EAED] bg-[#F7F9FA] px-4 py-3 outline-none transition focus:border-aurora"
        />
      </label>

      <div className="mt-5 flex flex-wrap gap-2">
        {selected.length > 0 ? (
          selected.map((code) => (
            <button
              key={code}
              type="button"
              onClick={() => toggleColor(code)}
              className="rounded-full border border-ink bg-ink px-3 py-2 text-xs font-bold uppercase tracking-[0.16em] text-white"
            >
              {code}
              {data?.[code]?.en ? ` · ${data[code].en}` : ''}
            </button>
          ))
        ) : (
          <span className="text-sm text-steel">尚未选择颜色。</span>
        )}
      </div>

      <div className="mt-6 rounded-3xl border border-[#E8EAED]">
        <div className="flex items-center justify-between border-b border-[#E8EAED] px-4 py-3">
          <div className="text-sm font-semibold text-ink">颜色池</div>
          <div className="text-xs font-bold uppercase tracking-[0.18em] text-steel">
            {selected.length} selected
          </div>
        </div>
        <div className="grid max-h-80 gap-2 overflow-y-auto p-4 sm:grid-cols-2">
          {isLoading ? <div className="text-sm text-steel">加载颜色映射中...</div> : null}
          {isError ? <div className="text-sm text-red-600">颜色映射加载失败，请稍后重试。</div> : null}
          {!isLoading && !isError && colorEntries.length === 0 ? (
            <div className="text-sm text-steel">没有匹配的颜色结果。</div>
          ) : null}
          {!isLoading && !isError
            ? colorEntries.map(([code, names]) => {
                const active = selected.includes(code);
                return (
                  <label
                    key={code}
                    className={[
                      'flex cursor-pointer items-start gap-3  border px-4 py-3 transition',
                      active
                        ? 'border-ink bg-ink text-white'
                        : 'border-[#E8EAED] bg-[#F7F9FA] hover:border-signal hover:bg-white',
                    ].join(' ')}
                  >
                    <input
                      type="checkbox"
                      checked={active}
                      onChange={() => toggleColor(code)}
                      className="mt-1 h-4 w-4  border-[#E8EAED]"
                    />
                    <span className="min-w-0">
                      <span className="block text-sm font-bold uppercase">{code}</span>
                      <span className={active ? 'mt-1 block text-xs text-[#8C8C8C]' : 'mt-1 block text-xs text-steel'}>
                        {names.en}
                      </span>
                    </span>
                  </label>
                );
              })
            : null}
        </div>
      </div>
    </section>
  );
}
