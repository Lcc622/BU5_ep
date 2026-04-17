import { useState } from 'react';
import { CountrySelector } from './components/CountrySelector/CountrySelector';
import { ColorMappingManager } from './components/ColorMapping/ColorMappingManager';
import { DownloadHistory } from './components/DownloadHistory/DownloadHistory';
import { ColorSelector } from './components/ExcelProcess/ColorSelector';
import { CountryTemplateSelector } from './components/ExcelProcess/CountryTemplateSelector';
import { DirectSkuInput } from './components/ExcelProcess/DirectSkuInput';
import { InputModeSwitcher } from './components/ExcelProcess/InputModeSwitcher';
import { PrefixInput } from './components/ExcelProcess/PrefixInput';
import { ProcessButton } from './components/ExcelProcess/ProcessButton';
import { FileUploader } from './components/ExcelUpload/FileUploader';
import { useProcessStore } from './store/useProcessStore';
import FollowSell from './pages/FollowSell';

type TabKey = 'process' | 'mapping' | 'history' | 'follow-sell';

function App() {
  const [activeTab, setActiveTab] = useState<TabKey>('process');
  const inputMode = useProcessStore((state) => state.inputMode);
  const isEmbed = new URLSearchParams(window.location.search).get('embed') === '1';

  return (
    <div className="min-h-screen">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {!isEmbed && (
          <header className="relative overflow-hidden rounded-[36px] border border-white/70 bg-[linear-gradient(135deg,#16212f_0%,#1d3557_42%,#0c7b93_100%)] px-6 py-8 text-white shadow-panel sm:px-8">
            <div className="absolute inset-0 bg-grid-fade bg-[size:24px_24px] opacity-20" />
            <div className="relative flex flex-wrap items-start justify-between gap-6">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.34em] text-[#8C8C8C]">AMZEU Operations Deck</p>
                <h1 className="mt-3 text-3xl font-extrabold sm:text-4xl">AMZEU-AI 加色加码</h1>
                <p className="mt-3 max-w-2xl text-sm text-[#8C8C8C] sm:text-base">
                  面向 UK / FR / DE / IT / ES 的欧洲亚马逊加色加码前端骨架，覆盖上传、前缀分析、模板确认、颜色映射与处理入口。
                </p>
              </div>
              <div className="grid min-w-[240px] gap-3 sm:grid-cols-2">
                <div className="rounded-3xl border border-white/15 bg-white/10 p-4 backdrop-blur">
                  <div className="text-xs font-bold uppercase tracking-[0.18em] text-[#8C8C8C]">Coverage</div>
                  <div className="mt-2 text-3xl font-extrabold">5</div>
                  <div className="mt-1 text-sm text-[#8C8C8C]">EU countries</div>
                </div>
                <div className="rounded-3xl border border-white/15 bg-white/10 p-4 backdrop-blur">
                  <div className="text-xs font-bold uppercase tracking-[0.18em] text-[#8C8C8C]">Modules</div>
                  <div className="mt-2 text-3xl font-extrabold">3</div>
                  <div className="mt-1 text-sm text-[#8C8C8C]">Process + mapping + history</div>
                </div>
              </div>
            </div>
          </header>
        )}

        <div className={isEmbed ? 'flex gap-3' : 'mt-6 flex gap-3'}>
          {[
            { key: 'process' as const, label: '加色加码' },
            { key: 'mapping' as const, label: '颜色映射管理' },
            { key: 'follow-sell' as const, label: '跟卖上新' },
            { key: 'history' as const, label: '下载历史' },
          ].map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={[
                'rounded-full px-5 py-3 text-sm font-semibold transition',
                activeTab === tab.key
                  ? 'bg-ink text-white '
                  : 'bg-white text-steel hover:text-ink',
              ].join(' ')}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <main className="mt-6 space-y-6">
          {activeTab === 'process' ? (
            <>
              <CountrySelector />
              <FileUploader />
              <CountryTemplateSelector />
              <InputModeSwitcher />
              <div className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
                <div className="space-y-6">
                  {inputMode === 'matrix' ? <PrefixInput /> : <DirectSkuInput />}
                </div>
                <div className="space-y-6">
                  {inputMode === 'matrix' ? <ColorSelector /> : null}
                  <ProcessButton />
                </div>
              </div>
            </>
          ) : activeTab === 'mapping' ? (
            <ColorMappingManager />
          ) : activeTab === 'follow-sell' ? (
            <FollowSell />
          ) : (
            <DownloadHistory />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
