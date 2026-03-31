import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Country } from '../types/api';

type ProcessMode = 'add-color' | 'add-code';
type InputMode = 'matrix' | 'direct-sku';

interface ProcessStore {
  country: Country;
  setCountry: (country: Country) => void;
  mode: ProcessMode;
  setMode: (mode: ProcessMode) => void;
  inputMode: InputMode;
  setInputMode: (mode: InputMode) => void;
  productPrefix: string;
  setProductPrefix: (prefix: string) => void;
  colorList: string;
  setColorList: (colorList: string) => void;
  directSkuText: string;
  setDirectSkuText: (value: string) => void;
  startSize: string;
  setStartSize: (size: string) => void;
  endSize: string;
  setEndSize: (size: string) => void;
  sizeStep: number;
  setSizeStep: (step: number) => void;
  generatedSkus: string[];
  generateSKUs: () => string[];
}

const parseColorCodes = (value: string) =>
  value
    .split(/[,，、;\s]+/)
    .map((item) => item.trim().toUpperCase())
    .filter((item) => item.length > 0);

export const useProcessStore = create<ProcessStore>()(
  persist(
    (set, get) => ({
      country: 'UK',
      setCountry: (country) => set({ country }),
      mode: 'add-color',
      setMode: (mode) => set({ mode }),
      inputMode: 'matrix',
      setInputMode: (inputMode) => set({ inputMode }),
      productPrefix: '',
      setProductPrefix: (productPrefix) => set({ productPrefix }),
      colorList: '',
      setColorList: (colorList) => set({ colorList }),
      directSkuText: '',
      setDirectSkuText: (directSkuText) => set({ directSkuText }),
      startSize: '04',
      setStartSize: (startSize) => set({ startSize }),
      endSize: '18',
      setEndSize: (endSize) => set({ endSize }),
      sizeStep: 2,
      setSizeStep: (sizeStep) => set({ sizeStep }),
      generatedSkus: [],
      generateSKUs: () => {
        const { productPrefix, colorList, startSize, endSize, sizeStep } = get();
        const prefix = productPrefix.trim().toUpperCase();
        const colors = parseColorCodes(colorList);

        if (!/^[A-Z0-9]{7,8}$/.test(prefix) || colors.length === 0) {
          set({ generatedSkus: [] });
          return [];
        }

        const start = Number.parseInt(startSize, 10);
        const end = Number.parseInt(endSize, 10);

        if (Number.isNaN(start) || Number.isNaN(end) || start > end || sizeStep <= 0) {
          set({ generatedSkus: [] });
          return [];
        }

        const sizes: string[] = [];
        for (let size = start; size <= end; size += sizeStep) {
          sizes.push(String(size).padStart(2, '0'));
        }

        const generatedSkus = colors.flatMap((color) =>
          sizes.map((size) => `${prefix}${color}${size}`)
        );

        set({ generatedSkus });
        return generatedSkus;
      },
    }),
    {
      name: 'amzeu-process-store',
      partialize: (state) => ({
        country: state.country,
        mode: state.mode,
        inputMode: state.inputMode,
        colorList: state.colorList,
        directSkuText: state.directSkuText,
        startSize: state.startSize,
        endSize: state.endSize,
        sizeStep: state.sizeStep,
      }),
    }
  )
);
