import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AnalysisResult, UploadedFilesResponse } from '../types/api';

interface CountryUploadState {
  allListingsFiles: string[];
  pzCategoryFiles: string[];
  epCategoryFiles: string[];
  analysisResult: AnalysisResult | null;
  selectedPrefixes: string[];
}

interface FileSyncResult {
  allListingsMissing: boolean;
  allListingsChanged: boolean;
  missingCategoryFiles: string[];
}

const createEmptyCountryState = (): CountryUploadState => ({
  allListingsFiles: [],
  pzCategoryFiles: [],
  epCategoryFiles: [],
  analysisResult: null,
  selectedPrefixes: [],
});

interface UploadStore {
  filesByCountry: Record<string, CountryUploadState>;
  getAllListingsFiles: (country: string) => string[];
  getPzCategoryFiles: (country: string) => string[];
  getEpCategoryFiles: (country: string) => string[];
  getAnalysisResult: (country: string) => AnalysisResult | null;
  getSelectedPrefixes: (country: string) => string[];
  addAllListingsFile: (country: string, filename: string) => void;
  removeAllListingsFile: (country: string, filename: string) => void;
  addPzCategoryFile: (country: string, filename: string) => void;
  removePzCategoryFile: (country: string, filename: string) => void;
  addEpCategoryFile: (country: string, filename: string) => void;
  removeEpCategoryFile: (country: string, filename: string) => void;
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
      getAllListingsFiles: (country) =>
        get().filesByCountry[country]?.allListingsFiles ?? [],
      getPzCategoryFiles: (country) =>
        get().filesByCountry[country]?.pzCategoryFiles ?? [],
      getEpCategoryFiles: (country) =>
        get().filesByCountry[country]?.epCategoryFiles ?? [],
      getAnalysisResult: (country) =>
        get().filesByCountry[country]?.analysisResult ?? null,
      getSelectedPrefixes: (country) =>
        get().filesByCountry[country]?.selectedPrefixes ?? [],
      addAllListingsFile: (country, filename) =>
        set((state) => {
          const countryState = state.filesByCountry[country] ?? createEmptyCountryState();
          return {
            filesByCountry: {
              ...state.filesByCountry,
              [country]: {
                ...countryState,
                allListingsFiles: dedupeFilenames([...countryState.allListingsFiles, filename]),
              },
            },
          };
        }),
      removeAllListingsFile: (country, filename) =>
        set((state) => {
          const countryState = state.filesByCountry[country] ?? createEmptyCountryState();
          const nextAllListingsFiles = countryState.allListingsFiles.filter((file) => file !== filename);
          const analysisMatchesDeletedFile = countryState.analysisResult?.filename === filename;
          return {
            filesByCountry: {
              ...state.filesByCountry,
              [country]: {
                ...countryState,
                allListingsFiles: nextAllListingsFiles,
                analysisResult: analysisMatchesDeletedFile ? null : countryState.analysisResult,
                selectedPrefixes: analysisMatchesDeletedFile ? [] : countryState.selectedPrefixes,
              },
            },
          };
        }),
      addPzCategoryFile: (country, filename) =>
        set((state) => {
          const countryState = state.filesByCountry[country] ?? createEmptyCountryState();
          return {
            filesByCountry: {
              ...state.filesByCountry,
              [country]: {
                ...countryState,
                pzCategoryFiles: dedupeFilenames([...countryState.pzCategoryFiles, filename]),
              },
            },
          };
        }),
      removePzCategoryFile: (country, filename) =>
        set((state) => {
          const countryState = state.filesByCountry[country] ?? createEmptyCountryState();
          return {
            filesByCountry: {
              ...state.filesByCountry,
              [country]: {
                ...countryState,
                pzCategoryFiles: countryState.pzCategoryFiles.filter((file) => file !== filename),
              },
            },
          };
        }),
      addEpCategoryFile: (country, filename) =>
        set((state) => {
          const countryState = state.filesByCountry[country] ?? createEmptyCountryState();
          return {
            filesByCountry: {
              ...state.filesByCountry,
              [country]: {
                ...countryState,
                epCategoryFiles: dedupeFilenames([...countryState.epCategoryFiles, filename]),
              },
            },
          };
        }),
      removeEpCategoryFile: (country, filename) =>
        set((state) => {
          const countryState = state.filesByCountry[country] ?? createEmptyCountryState();
          return {
            filesByCountry: {
              ...state.filesByCountry,
              [country]: {
                ...countryState,
                epCategoryFiles: countryState.epCategoryFiles.filter((file) => file !== filename),
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
        const currentAllListingsFiles = dedupeFilenames(countryState.allListingsFiles);
        const nextAllListingsFiles = dedupeFilenames(files.all_listings);
        const nextPzCategoryFiles = dedupeFilenames(files.pz_category_listings);
        const nextEpCategoryFiles = dedupeFilenames(files.ep_category_listings);
        const allListingsMissing =
          currentAllListingsFiles.length > 0 &&
          currentAllListingsFiles.some((filename) => !nextAllListingsFiles.includes(filename));
        const allListingsChanged =
          currentAllListingsFiles.length > 0 &&
          (
            currentAllListingsFiles.length !== nextAllListingsFiles.length ||
            currentAllListingsFiles.some((filename, index) => filename !== nextAllListingsFiles[index])
          );
        const currentCategoryFiles = dedupeFilenames([
          ...countryState.pzCategoryFiles,
          ...countryState.epCategoryFiles,
        ]);
        const nextCategoryFiles = dedupeFilenames([
          ...nextPzCategoryFiles,
          ...nextEpCategoryFiles,
        ]);
        const missingCategoryFiles = currentCategoryFiles.filter((filename) => !nextCategoryFiles.includes(filename));
        const analysisFilename = countryState.analysisResult?.filename?.trim();
        const preserveAnalysis =
          Boolean(analysisFilename) && nextAllListingsFiles.includes(analysisFilename ?? '');

        set((state) => ({
          filesByCountry: {
            ...state.filesByCountry,
            [country]: {
              ...createEmptyCountryState(),
              ...countryState,
              allListingsFiles: nextAllListingsFiles,
              pzCategoryFiles: nextPzCategoryFiles,
              epCategoryFiles: nextEpCategoryFiles,
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
    {
      name: 'amzeu-upload-store',
      version: 2,
      migrate: (state, version) => {
        if (!state || typeof state !== 'object') {
          return state;
        }

        if (version === 0 || version === 1) {
          const persistedState = state as {
            filesByCountry?: Record<string, Record<string, unknown>>;
          };

          if (persistedState.filesByCountry) {
            for (const countryState of Object.values(persistedState.filesByCountry)) {
              delete countryState.categoryFiles;
              countryState.pzCategoryFiles = [];
              countryState.epCategoryFiles = [];
            }
          }
        }

        return state;
      },
    }
  )
);
