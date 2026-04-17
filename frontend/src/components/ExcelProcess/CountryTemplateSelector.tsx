import { getCountryMeta, TEMPLATE_MAP } from '../../constants/countries';
import { useProcessStore } from '../../store/useProcessStore';

export function CountryTemplateSelector() {
  const country = useProcessStore((state) => state.country);
  const meta = getCountryMeta(country);
  const template = TEMPLATE_MAP[country];

  return (
    <section className="rounded-[28px] border border-[#E8EAED] bg-white p-6 shadow-panel">
      <p className="text-xs font-bold uppercase tracking-[0.32em] text-aurora">Template</p>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-xl font-extrabold text-ink">{meta.flag} {country} 模板</h3>
          <p className="mt-1 text-sm text-steel">当前模板只读展示，用于确认处理目标国家和模板文件。</p>
        </div>
        <div className="rounded-full bg-ink px-3 py-1 text-xs font-bold uppercase tracking-[0.2em] text-white">
          {template.required_category_reports} reports required
        </div>
      </div>
      <div className="mt-5 rounded-3xl bg-mist p-5">
        <div className="text-sm font-semibold text-steel">Template Name</div>
        <div className="mt-2 break-all text-lg font-bold text-ink">{template.template_name}</div>
      </div>
    </section>
  );
}
