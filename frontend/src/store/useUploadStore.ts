import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AnalysisResult, UploadedFilesResponse } from '../types/api';

interface CountryUploadState {
  allListingsFile: string | null;
  categoryFiles: string[];
  analysisResult: AnalysisResult | null;
  selectedPrefixes: string[];
}

interface FileSyncResult {
  allListingsMissing: boolean;
  allListingsChanged: boolean;
  missingCategoryFiles: string[];
}

const createEmptyCountryState = (): CountryUploadState => ({
  allListingsFile: null,
  categoryFiles: [],
  analysisResult: null,
  selectedPrefixes: [],
});

interface UploadStore {
  filesByCountry: Record<string, CountryUploadState>;
  getAllListingsFile: (country: string) => string | null;
  getCategoryFiles: (country: string) => string[];
  getAnalysisResult: (country: string) => AnalysisResult | null;
  getSelectedPrefixes: (country: string) => string[];
  setAllListingsFile: (country: string, filename: string | null) => void;
  setCategoryFiles: (country: string, filenames: string[]) => void;
  addCategoryFile: (country: string, filename: string) => void;
  removeCategoryFile: (country: string, filename: string) => void;
  setAnalysisResult: (country: string, result: AnalysisResult | null) => void;
  setSelectedPrefixes: (country: string, prefixes: string[]) => void;
  syncUploadedFiles: (country: string, files: UploadedFilesResponse) => FileSyncResult;
  clearCountryFiles: (country: string) => void;
}

const dedupeFilenames = (filenames: string[]) =>
  Array.from(
    new Set(
      filenames
        .map((filename) => filename.trim())
        .filter(Boolean)
    )
  );

export const useUploadStore = create<UploadStore>()(
  persist(
    (set, get) => ({
      filesByCountry: {},
      getAllListingsFile: (country) =>
        get().filesByCountry[country]?.allListingsFile ?? null,
      getCategoryFiles: (country) =>
        get().filesByCountry[country]?.categoryFiles ?? [],
      getAnalysisResult: (country) =>
        get().filesByCountry[country]?.analysisResult ?? null,
      getSelectedPrefixes: (country) =>
        get().filesByCountry[country]?.selectedPrefixes ?? [],
      setAllListingsFile: (country, filename) =>
        set((state) => ({
          filesByCountry: {
            ...state.filesByCountry,
            [country]: {
              ...createEmptyCountryState(),
              ...state.filesByCountry[country],
              allListingsFile: filename,
            },
          },
        })),
      setCategoryFiles: (country, filenames) =>
        set((state) => ({
          filesByCountry: {
            ...state.filesByCountry,
            [country]: {
              ...createEmptyCountryState(),
              ...state.filesByCountry[country],
              categoryFiles: dedupeFilenames(filenames),
            },
          },
        })),
      addCategoryFile: (country, filename) =>
        set((state) => {
          const countryState = state.filesByCountry[country] ?? createEmptyCountryState();
          return {
            filesByCountry: {
              ...state.filesByCountry,
              [country]: {
                ...countryState,
                categoryFiles: countryState.categoryFiles.includes(filename)
                  ? countryState.categoryFiles
                  : [...countryState.categoryFiles, filename],
              },
            },
          };
        }),
      removeCategoryFile: (country, filename) =>
        set((state) => {
          const countryState = state.filesByCountry[country] ?? createEmptyCountryState();
          return {
            filesByCountry: {
              ...state.filesByCountry,
              [country]: {
                ...countryState,
                categoryFiles: countryState.categoryFiles.filter((file) => file !== filename),
              },
            },
          };
        }),
      setAnalysisResult: (country, analysisResult) =>
        set((state) => ({
          filesByCountry: {
            ...state.filesByCountry,
            [country]: {
              ...createEmptyCountryState(),
              ...state.filesByCountry[country],
              analysisResult,
            },
          },
        })),
      setSelectedPrefixes: (country, selectedPrefixes) =>
        set((state) => ({
          filesByCountry: {
            ...state.filesByCountry,
            [country]: {
              ...createEmptyCountryState(),
              ...state.filesByCountry[country],
              selectedPrefixes,
            },
          },
        })),
      syncUploadedFiles: (country, files) => {
        const countryState = get().filesByCountry[country] ?? createEmptyCountryState();
        const currentAllListingsFile = countryState.allListingsFile;
        const nextAllListingsFile = files.all_listings[0] ?? null;
        const nextCategoryFiles = dedupeFilenames(files.category_listings);
        const allListingsMissing =
          currentAllListingsFile !== null &&
          !files.all_listings.includes(currentAllListingsFile);
        const allListingsChanged =
          currentAllListingsFile !== null &&
          currentAllListingsFile !== nextAllListingsFile;
        const missingCategoryFiles = countryState.categoryFiles.filter(
          (filename) => !nextCategoryFiles.includes(filename)
        );
        const preserveAnalysis = currentAllListingsFile === nextAllListingsFile;

        set((state) => ({
          filesByCountry: {
            ...state.filesByCountry,
            [country]: {
              ...createEmptyCountryState(),
              ...countryState,
              allListingsFile: nextAllListingsFile,
              categoryFiles: nextCategoryFiles,
              analysisResult: preserveAnalysis ? countryState.analysisResult : null,
              selectedPrefixes: preserveAnalysis ? countryState.selectedPrefixes : [],
            },
          },
        }));

        return {
          allListingsMissing,
          allListingsChanged,
          missingCategoryFiles,
        };
      },
      clearCountryFiles: (country) =>
        set((state) => ({
          filesByCountry: {
            ...state.filesByCountry,
            [country]: createEmptyCountryState(),
          },
        })),
    }),
    { name: 'amzeu-upload-store' }
  )
);
