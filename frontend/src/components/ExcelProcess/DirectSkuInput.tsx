import { parseDirectSkuText } from './directSku';
import { useProcessStore } from '../../store/useProcessStore';

export function DirectSkuInput() {
  const directSkuText = useProcessStore((state) => state.directSkuText);
  const setDirectSkuText = useProcessStore((state) => state.setDirectSkuText);
  const parsed = parseDirectSkuText(directSkuText);
  const invalidPreview = parsed.invalidEntries.slice(0, 6);

  return (
    <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-panel">
      <p className="text-xs font-bold uppercase tracking-[0.32em] text-signal">Direct SKU</p>
      <h3 className="mt-2 text-xl font-extrabold text-ink">直接粘贴目标 SKU</h3>
      <p className="mt-2 text-sm text-steel">
        支持换行、逗号、空格分隔。格式为 7-8 位产品码 + 2 位颜色码 + 2 位尺码，可选后缀如
        <span className="mx-1 font-mono font-semibold text-aurora">-EU</span>
        或
        <span className="ml-1 font-mono font-semibold text-aurora">-UK14</span>
        。
      </p>

      <label className="mt-5 block">
        <span className="mb-2 block text-sm font-semibold text-ink">SKU 文本</span>
        <textarea
          rows={8}
          value={directSkuText}
          onChange={(event) => setDirectSkuText(event.target.value)}
          placeholder={'例如：\nB0ABCDEBK08\nB0ABCDEBK10, B0ABCDEWH08-EU\n12345678RD12 12345678BK14-UK14'}
          className="w-full rounded-3xl border border-slate-200 bg-slate-50 px-4 py-3 font-mono text-sm uppercase outline-none transition focus:border-aurora"
        />
      </label>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl bg-mist p-4">
          <div className="text-xs font-bold uppercase tracking-[0.18em] text-steel">SKU 数</div>
          <div className="mt-2 text-2xl font-extrabold text-ink">{parsed.uniqueSkus.length}</div>
        </div>
        <div className="rounded-2xl bg-mist p-4">
          <div className="text-xs font-bold uppercase tracking-[0.18em] text-steel">产品码数</div>
          <div className="mt-2 text-2xl font-extrabold text-ink">{parsed.productCodes.length}</div>
        </div>
        <div className="rounded-2xl bg-mist p-4">
          <div className="text-xs font-bold uppercase tracking-[0.18em] text-steel">颜色数</div>
          <div className="mt-2 text-2xl font-extrabold text-ink">{parsed.colorCodes.length}</div>
        </div>
      </div>

      {parsed.duplicateCount > 0 ? (
        <div className="mt-4 rounded-3xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
          检测到 {parsed.duplicateCount} 个重复 SKU，提交时会自动去重。
        </div>
      ) : null}

      {parsed.invalidEntries.length > 0 ? (
        <div className="mt-4 rounded-3xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <div className="font-semibold">以下 SKU 格式不正确：</div>
          <div className="mt-2 font-mono text-xs uppercase leading-6">
            {invalidPreview.join(' / ')}
            {parsed.invalidEntries.length > invalidPreview.length
              ? ` / 另有 ${parsed.invalidEntries.length - invalidPreview.length} 个未展示`
              : ''}
          </div>
        </div>
      ) : directSkuText.trim() ? (
        <div className="mt-4 rounded-3xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          SKU 文本校验通过，可以直接提交处理。
        </div>
      ) : null}

      <div className="mt-5 rounded-3xl bg-mist p-4">
        <div className="text-sm font-semibold text-ink">Preview</div>
        <div className="mt-3 flex max-h-40 flex-wrap gap-2 overflow-y-auto">
          {parsed.uniqueSkus.length > 0 ? (
            parsed.uniqueSkus.slice(0, 18).map((sku) => (
              <span
                key={sku}
                className="rounded-full border border-slate-300 bg-white px-3 py-2 text-xs font-bold tracking-[0.12em] text-ink"
              >
                {sku}
              </span>
            ))
          ) : (
            <span className="text-sm text-steel">粘贴 SKU 后，这里会显示标准化预览。</span>
          )}
        </div>
      </div>
    </section>
  );
}
