import { FormEvent, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import type { ColorMapping, ColorNames } from '../../types/api';
import { mappingApi } from '../../services/mappingApi';

const LANGS: { key: keyof ColorNames; label: string }[] = [
  { key: 'en', label: 'EN' },
  { key: 'fr', label: 'FR' },
  { key: 'de', label: 'DE' },
  { key: 'it', label: 'IT' },
  { key: 'es', label: 'ES' },
];

const EMPTY_NAMES: ColorNames = { en: '', fr: '', de: '', it: '', es: '' };

const normalizeColorNames = (value: unknown): ColorNames => {
  if (!value || typeof value !== 'object') {
    return { ...EMPTY_NAMES };
  }

  const source = value as Partial<Record<keyof ColorNames, unknown>>;

  return {
    en: typeof source.en === 'string' ? source.en : '',
    fr: typeof source.fr === 'string' ? source.fr : '',
    de: typeof source.de === 'string' ? source.de : '',
    it: typeof source.it === 'string' ? source.it : '',
    es: typeof source.es === 'string' ? source.es : '',
  };
};

const normalizeColorMapping = (value: unknown): ColorMapping => {
  if (!value || typeof value !== 'object') {
    return {};
  }

  return Object.fromEntries(
    Object.entries(value).map(([code, names]) => [code, normalizeColorNames(names)])
  );
};

export function ColorMappingManager() {
  const queryClient = useQueryClient();
  const [keyword, setKeyword] = useState('');
  const [displayMappings, setDisplayMappings] = useState<ColorMapping>({});
  const [newCode, setNewCode] = useState('');
  const [newNames, setNewNames] = useState<ColorNames>({ ...EMPTY_NAMES });

  const { data, isLoading, isError } = useQuery({
    queryKey: ['mappings'],
    queryFn: async () => normalizeColorMapping(await mappingApi.getAllMappings()),
  });

  useEffect(() => {
    setDisplayMappings(data ?? {});
  }, [data]);

  const searchMutation = useMutation({
    mutationFn: async (query: string) => {
      const trimmed = query.trim();
      if (!trimmed) {
        return data ?? {};
      }
      return normalizeColorMapping(await mappingApi.searchMappings(trimmed));
    },
    onSuccess: (result) => {
      setDisplayMappings(result);
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : '搜索失败');
    },
  });

  const addMutation = useMutation({
    mutationFn: async ({ code, names }: { code: string; names: ColorNames }) =>
      mappingApi.addMapping(code, names),
    onSuccess: async () => {
      setNewCode('');
      setNewNames({ ...EMPTY_NAMES });
      await queryClient.invalidateQueries({ queryKey: ['mappings'] });
      if (keyword.trim()) {
        searchMutation.mutate(keyword);
      }
      toast.success('颜色映射已保存');
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : '保存失败');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (code: string) => mappingApi.deleteMapping(code),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['mappings'] });
      if (keyword.trim()) {
        searchMutation.mutate(keyword);
      }
      toast.success('颜色映射已删除');
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : '删除失败');
    },
  });

  const entries = Object.entries(displayMappings).sort(([leftCode], [rightCode]) =>
    leftCode.localeCompare(rightCode)
  );

  const handleSearch = (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    searchMutation.mutate(keyword);
  };

  const handleCreate = () => {
    const code = newCode.trim().toUpperCase();
    if (!code || !newNames.en.trim()) {
      toast.error('请填写颜色代码和英文名称（EN 为必填）');
      return;
    }
    addMutation.mutate({ code, names: newNames });
  };

  return (
    <section className="rounded-[32px] border border-slate-200 bg-white p-6 shadow-panel">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.32em] text-signal">Mapping Console</p>
          <h2 className="mt-2 text-2xl font-extrabold text-ink">颜色映射管理</h2>
          <p className="mt-2 text-sm text-steel">支持搜索、添加和删除颜色映射，每个颜色码支持 EN / FR / DE / IT / ES 多语言名称。</p>
        </div>
        <div className="rounded-full bg-mist px-4 py-2 text-sm font-semibold text-ink">
          {entries.length} mappings
        </div>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div>
          <form onSubmit={handleSearch} className="flex gap-3">
            <input
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              placeholder="搜索颜色代码或名称"
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none transition focus:border-aurora"
            />
            <button
              type="submit"
              disabled={searchMutation.isPending}
              className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60"
            >
              搜索
            </button>
            <button
              type="button"
              onClick={() => {
                setKeyword('');
                setDisplayMappings(data ?? {});
              }}
              className="rounded-full border border-slate-300 px-5 py-3 text-sm font-semibold text-steel transition hover:border-ink hover:text-ink"
            >
              清空
            </button>
          </form>

          <div className="mt-4 overflow-hidden rounded-3xl border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-[0.18em] text-steel">Code</th>
                  <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-[0.18em] text-steel">EN</th>
                  <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-[0.18em] text-steel">FR</th>
                  <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-[0.18em] text-steel">DE</th>
                  <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-[0.18em] text-steel">IT</th>
                  <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-[0.18em] text-steel">ES</th>
                  <th className="px-4 py-3 text-right text-xs font-bold uppercase tracking-[0.18em] text-steel">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {isLoading ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-6 text-sm text-steel">加载中...</td>
                  </tr>
                ) : null}
                {isError ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-6 text-sm text-red-600">颜色映射加载失败。</td>
                  </tr>
                ) : null}
                {!isLoading && !isError && entries.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-6 text-sm text-steel">没有匹配的映射。</td>
                  </tr>
                ) : null}
                {!isLoading && !isError
                  ? entries.map(([code, names]) => (
                      <tr key={code}>
                        <td className="px-4 py-4 font-mono text-sm font-bold text-ink">{code}</td>
                        <td className="px-4 py-4 text-sm text-steel">{names.en}</td>
                        <td className="px-4 py-4 text-sm text-slate-400">{names.fr || '—'}</td>
                        <td className="px-4 py-4 text-sm text-slate-400">{names.de || '—'}</td>
                        <td className="px-4 py-4 text-sm text-slate-400">{names.it || '—'}</td>
                        <td className="px-4 py-4 text-sm text-slate-400">{names.es || '—'}</td>
                        <td className="px-4 py-4 text-right">
                          <button
                            type="button"
                            onClick={() => deleteMutation.mutate(code)}
                            disabled={deleteMutation.isPending}
                            className="text-sm font-semibold text-red-600 transition hover:text-red-700 disabled:opacity-60"
                          >
                            删除
                          </button>
                        </td>
                      </tr>
                    ))
                  : null}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-3xl bg-mist p-5">
          <div className="text-lg font-bold text-ink">添加映射</div>
          <div className="mt-4 space-y-3">
            <input
              value={newCode}
              onChange={(event) => setNewCode(event.target.value.toUpperCase())}
              placeholder="颜色代码，例如 BK"
              maxLength={2}
              className="w-full rounded-2xl border border-white bg-white px-4 py-3 outline-none transition focus:border-signal"
            />
            {LANGS.map(({ key, label }) => (
              <div key={key} className="flex items-center gap-2">
                <span className="w-8 flex-shrink-0 text-xs font-bold text-steel">{label}</span>
                <input
                  value={newNames[key]}
                  onChange={(event) =>
                    setNewNames((prev) => ({ ...prev, [key]: event.target.value }))
                  }
                  placeholder={key === 'en' ? `颜色名称（必填）` : `颜色名称（选填）`}
                  className="w-full rounded-2xl border border-white bg-white px-4 py-2.5 text-sm outline-none transition focus:border-signal"
                />
              </div>
            ))}
            <button
              type="button"
              onClick={handleCreate}
              disabled={addMutation.isPending}
              className="w-full rounded-full bg-signal px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-60"
            >
              {addMutation.isPending ? '保存中...' : '保存映射'}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
