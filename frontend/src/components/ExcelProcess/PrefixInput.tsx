import { useEffect } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { useProcessStore } from '../../store/useProcessStore';
import { useUploadStore } from '../../store/useUploadStore';

export function PrefixInput() {
  const country = useProcessStore((state) => state.country);
  const productPrefix = useProcessStore((state) => state.productPrefix);
  const setProductPrefix = useProcessStore((state) => state.setProductPrefix);
  const startSize = useProcessStore((state) => state.startSize);
  const setStartSize = useProcessStore((state) => state.setStartSize);
  const endSize = useProcessStore((state) => state.endSize);
  const setEndSize = useProcessStore((state) => state.setEndSize);
  const sizeStep = useProcessStore((state) => state.sizeStep);
  const setSizeStep = useProcessStore((state) => state.setSizeStep);
  const generateSKUs = useProcessStore((state) => state.generateSKUs);
  const generatedSkus = useProcessStore((state) => state.generatedSkus);

  const selectedPrefixes = useUploadStore(
    useShallow((state) => state.filesByCountry[country]?.selectedPrefixes ?? [])
  );

  // Auto-sync first selected prefix into preview
  useEffect(() => {
    if (selectedPrefixes.length > 0) {
      setProductPrefix(selectedPrefixes[0]);
    } else {
      setProductPrefix('');
    }
  }, [selectedPrefixes, setProductPrefix]);

  return (
    <section className="rounded-[28px] border border-[#E8EAED] bg-white p-6 shadow-panel">
      <p className="text-xs font-bold uppercase tracking-[0.32em] text-signal">SKU Generator</p>
      <h3 className="mt-2 text-xl font-extrabold text-ink">尺码区间预览</h3>

      <div className="mt-4  bg-mist px-4 py-3 text-sm">
        {selectedPrefixes.length === 0 ? (
          <span className="text-steel">请先在前缀预检中勾选产品前缀</span>
        ) : (
          <span className="text-ink">
            将处理 <span className="font-bold">{selectedPrefixes.length}</span> 个前缀：
            <span className="ml-1 font-mono font-semibold text-aurora">{selectedPrefixes.join('  ')}</span>
            {selectedPrefixes.length > 1 && (
              <span className="ml-2 text-steel text-xs">（预览显示第一个）</span>
            )}
          </span>
        )}
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <label>
          <span className="mb-2 block text-sm font-semibold text-ink">起始尺码</span>
          <input
            value={startSize}
            onChange={(event) => setStartSize(event.target.value)}
            className="w-full  border border-[#E8EAED] bg-[#F7F9FA] px-4 py-3 outline-none transition focus:border-aurora"
          />
        </label>

        <label>
          <span className="mb-2 block text-sm font-semibold text-ink">结束尺码</span>
          <input
            value={endSize}
            onChange={(event) => setEndSize(event.target.value)}
            className="w-full  border border-[#E8EAED] bg-[#F7F9FA] px-4 py-3 outline-none transition focus:border-aurora"
          />
        </label>

        <label>
          <span className="mb-2 block text-sm font-semibold text-ink">尺码步长</span>
          <input
            type="number"
            min={1}
            value={sizeStep}
            onChange={(event) => setSizeStep(Number(event.target.value) || 1)}
            className="w-full  border border-[#E8EAED] bg-[#F7F9FA] px-4 py-3 outline-none transition focus:border-aurora"
          />
        </label>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-4">
        <button
          type="button"
          onClick={() => generateSKUs()}
          disabled={selectedPrefixes.length === 0}
          className="rounded-full bg-aurora px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          预生成 SKU
        </button>

        <div className="rounded-full bg-mist px-4 py-3 text-sm font-semibold text-ink">
          已生成 {generatedSkus.length} 条
        </div>
      </div>

      <div className="mt-5 rounded-3xl bg-mist p-4">
        <div className="text-sm font-semibold text-ink">
          SKU Preview
          {productPrefix && <span className="ml-2 text-xs font-normal text-steel">({productPrefix})</span>}
        </div>
        <div className="mt-3 flex max-h-40 flex-wrap gap-2 overflow-y-auto">
          {generatedSkus.length > 0 ? (
            generatedSkus.slice(0, 18).map((sku) => (
              <span
                key={sku}
                className="rounded-full border border-[#E8EAED] bg-white px-3 py-2 text-xs font-bold tracking-[0.12em] text-ink"
              >
                {sku}
              </span>
            ))
          ) : (
            <span className="text-sm text-steel">设置尺码区间后点击"预生成 SKU"预览。</span>
          )}
        </div>
      </div>
    </section>
  );
}
