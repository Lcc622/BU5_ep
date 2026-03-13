import { COUNTRIES } from '../../constants/countries';
import { useProcessStore } from '../../store/useProcessStore';

export function CountrySelector() {
  const country = useProcessStore((state) => state.country);
  const setCountry = useProcessStore((state) => state.setCountry);

  return (
    <section className="rounded-[28px] border border-white/60 bg-white/80 p-6 shadow-panel backdrop-blur">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.32em] text-signal">Marketplace</p>
          <h2 className="mt-2 text-2xl font-extrabold text-ink">选择欧洲站点</h2>
        </div>
        <p className="max-w-md text-sm text-steel">
          切换国家会同步刷新上传要求、模板提示和处理参数。各站点上传记录独立保存，方便来回切换核对。
        </p>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {COUNTRIES.map((item) => {
          const isActive = item.code === country;
          return (
            <button
              key={item.code}
              type="button"
              onClick={() => {
                if (item.code !== country) {
                  setCountry(item.code);
                }
              }}
              className={[
                'group rounded-3xl border px-4 py-4 text-left transition-all duration-200',
                isActive
                  ? 'border-ink bg-ink text-white shadow-lg'
                  : 'border-slate-200 bg-slate-50/80 text-ink hover:border-signal hover:bg-white',
              ].join(' ')}
            >
              <div className="flex items-center justify-between">
                <span className="text-2xl">{item.flag}</span>
                <span
                  className={[
                    'rounded-full px-2 py-1 text-[11px] font-bold uppercase tracking-[0.2em]',
                    isActive ? 'bg-white/15 text-white' : 'bg-slate-200 text-slate-700',
                  ].join(' ')}
                >
                  {item.code}
                </span>
              </div>
              <div className="mt-5">
                <div className="text-base font-bold">{item.label}</div>
                <div className={isActive ? 'mt-1 text-sm text-slate-200' : 'mt-1 text-sm text-steel'}>
                  Category Reports: {item.categoryReportCount}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
