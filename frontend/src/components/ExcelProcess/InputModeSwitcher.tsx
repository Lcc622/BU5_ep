import { useProcessStore } from '../../store/useProcessStore';

const INPUT_MODE_OPTIONS = [
  {
    value: 'matrix' as const,
    label: '选择模式',
    description: '按前缀、颜色和尺码区间批量生成 SKU。',
  },
  {
    value: 'direct-sku' as const,
    label: '直接贴 SKU',
    description: '直接粘贴目标 SKU，跳过前缀和颜色矩阵选择。',
  },
];

export function InputModeSwitcher() {
  const inputMode = useProcessStore((state) => state.inputMode);
  const setInputMode = useProcessStore((state) => state.setInputMode);
  const activeOption = INPUT_MODE_OPTIONS.find((option) => option.value === inputMode) ?? INPUT_MODE_OPTIONS[0];

  return (
    <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-panel">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.32em] text-aurora">Input Mode</p>
          <h3 className="mt-2 text-xl font-extrabold text-ink">选择输入方式</h3>
          <p className="mt-2 text-sm text-steel">{activeOption.description}</p>
        </div>
        <div className="inline-flex rounded-full bg-slate-100 p-1">
          {INPUT_MODE_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setInputMode(option.value)}
              className={[
                'rounded-full px-4 py-2 text-sm font-semibold transition',
                inputMode === option.value ? 'bg-ink text-white' : 'text-slate-500 hover:text-ink',
              ].join(' ')}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
