import { apiClient } from '../lib/axios';
import type {
  AnalysisResult,
  Country,
  ProcessJobStatusResponse,
  ProcessRequest,
  ProcessStartResponse,
  ResultsListResponse,
  UploadedFilesResponse,
} from '../types/api';

const buildApiPath = (pathname: string) => {
  const baseURL = apiClient.defaults.baseURL ?? '/';
  const normalizedBase = baseURL.endsWith('/') ? baseURL.slice(0, -1) : baseURL;
  const normalizedPath = pathname.startsWith('/') ? pathname : `/${pathname}`;
  return `${normalizedBase}${normalizedPath}`;
};

export const excelApi = {
  async uploadAllListings(file: File, country: Country): Promise<AnalysisResult & { filename?: string }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('country', country);

    const { data } = await apiClient.post<AnalysisResult & { filename?: string }>(
      '/api/excel/upload/listings',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return data;
  },

  async uploadCategoryListings(file: File, country: Country): Promise<{ success: boolean; filename: string }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('country', country);

    const { data } = await apiClient.post<{ success: boolean; filename: string }>(
      '/api/excel/upload/category',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return data;
  },

  async getUploadedFiles(country: Country): Promise<UploadedFilesResponse> {
    const { data } = await apiClient.get<UploadedFilesResponse>('/api/excel/files', {
      params: { country },
    });
    return data;
  },

  async deleteUploadedFile(filename: string): Promise<{ success: boolean; filename: string }> {
    const { data } = await apiClient.delete<{ success: boolean; filename: string }>(
      `/api/excel/files/uploaded?filename=${encodeURIComponent(filename)}`
    );
    return data;
  },

  async startProcess(request: ProcessRequest): Promise<ProcessStartResponse> {
    const { data } = await apiClient.post<ProcessStartResponse>('/api/excel/process', request);
    return data;
  },

  async getJobStatus(jobId: string): Promise<ProcessJobStatusResponse> {
    const { data } = await apiClient.get<ProcessJobStatusResponse>(`/api/excel/jobs/${jobId}`);
    return data;
  },

  async getResults(): Promise<ResultsListResponse> {
    const { data } = await apiClient.get<ResultsListResponse>('/api/excel/results');
    return data;
  },

  downloadResult(filename: string): string {
    return buildApiPath(`/api/excel/download/${encodeURIComponent(filename)}`);
  },
};
