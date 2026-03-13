import { apiClient } from '../lib/axios';
import type { ColorMapping, ColorMappingResponse, ColorMappingSearchResponse, ColorNames } from '../types/api';

export const mappingApi = {
  async getAllMappings(): Promise<ColorMapping> {
    const { data } = await apiClient.get<ColorMappingResponse>('/api/mapping');
    return data.data ?? {};
  },

  async addMapping(code: string, names: ColorNames): Promise<void> {
    await apiClient.post('/api/mapping', { code, names });
  },

  async deleteMapping(code: string): Promise<void> {
    await apiClient.delete(`/api/mapping/${encodeURIComponent(code)}`);
  },

  async searchMappings(keyword: string): Promise<ColorMapping> {
    const { data } = await apiClient.get<ColorMappingSearchResponse>('/api/mapping/search', {
      params: { keyword },
    });
    return data.data ?? {};
  },
};
