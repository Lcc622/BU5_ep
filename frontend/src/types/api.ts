export type Country = 'UK' | 'FR' | 'DE' | 'IT' | 'ES';

export interface ColorNames {
  en: string;
  fr: string;
  de: string;
  it: string;
  es: string;
}

export interface ColorMapping {
  [code: string]: ColorNames;
}

export interface ColorMappingResponse {
  success: boolean;
  data?: ColorMapping;
  message?: string;
}

export interface ColorMappingSearchResponse {
  success: boolean;
  data?: ColorMapping;
  count: number;
  message?: string;
}

export interface ColorDistributionItem {
  color_code: string;
  color_name: string | null;
  count: number;
}

export interface AnalysisResult {
  success: boolean;
  filename?: string;
  total_skus: number;
  prefixes: string[];
  suffixes: string[];
  color_distribution: ColorDistributionItem[];
}

export interface ProcessRequest {
  country: Country;
  all_listings_files: string[];
  category_files: string[];
  selected_prefixes: string[];
  target_colors: string[];
  start_size: string;
  end_size: string;
  size_step: number;
  mode: 'add-color' | 'add-code';
}

export interface ProcessStartResponse {
  job_id: string;
  status: 'pending';
}

export interface ProcessResult {
  output_file: string;
  processed_count: number;
  skipped_count: number;
}

export interface ProcessJobStatusResponse {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | string;
  progress: number;
  result?: ProcessResult;
  error?: string;
}

export interface FileInfo {
  filename: string;
  size: number;
  uploaded_at: string;
  country: Country;
  category?: 'all-listings' | 'category-listings';
}

export interface TemplateInfo {
  country: Country;
  template_name: string;
  required_category_reports: number;
}

export interface UploadedFilesResponse {
  all_listings: string[];
  pz_category_listings: string[];
  ep_category_listings: string[];
}

export interface ResultFileInfo {
  filename: string;
  modified_at: string;
  size?: number;
}

export interface ResultsListResponse {
  files: ResultFileInfo[];
}
