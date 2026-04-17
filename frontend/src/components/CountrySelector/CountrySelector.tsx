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
    'group border border-[#E8EAED] bg-white px-4 py-4 text-left transition-colors duration-200 hover:bg-[#F7F9FA]',
    isActive
     ? 'border-l-4 border-l-[#4D7B75] bg-[rgba(77,123,117,0.05)]'
     : '',
    ].join(' ')}
   >
    <div className="flex items-center justify-between">
    <span className="text-2xl">{item.flag}</span>
    <span className="bg-[#091E40] px-2 py-0.5 text-xs font-bold text-white">
     {item.code}
    </span>
    </div>
    <div className="mt-5">
    <div className="text-base font-bold text-[#091E40]">{item.label}</div>
    <div className="mt-1 text-sm text-[#8C8C8C]">
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
