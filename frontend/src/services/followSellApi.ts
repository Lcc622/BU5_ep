import { apiClient } from '../lib/axios';

export interface FollowSellRequest {
  country: string;
  all_listings_files: string[];
  category_files: string[];
  new_skus: string[];
  fr_all_listings_file?: string;
}

export interface FollowSellResult {
  output_file: string;
  processed_count: number;
  skipped_skus: string[];
  invalid_skus: string[];
  no_price_skus: string[];
  identity_skus: string[];
}

export interface FollowSellJobStatus {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  result: FollowSellResult | null;
  error: string | null;
}

export const followSellApi = {
  startProcess: async (req: FollowSellRequest): Promise<FollowSellJobStatus> => {
    const { data } = await apiClient.post<FollowSellJobStatus>('/api/follow-sell/process', req);
    return data;
  },

  pollStatus: async (jobId: string): Promise<FollowSellJobStatus> => {
    const { data } = await apiClient.get<FollowSellJobStatus>(`/api/follow-sell/status/${jobId}`);
    return data;
  },

  getDownloadUrl: (filename: string): string =>
    `/api/follow-sell/download/${encodeURIComponent(filename)}`,
};
