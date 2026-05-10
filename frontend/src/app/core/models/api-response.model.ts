export interface ApiError {
  detail: string | Array<{ msg: string; loc: string[] }>;
}

export interface ScrapeJob {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at: string | null;
  records_scraped: number;
  records_matched: number;
  error_message: string | null;
  source?: string;
}

export interface ExportResult {
  download_url: string;
  file_name: string;
  record_count: number;
  file_size_bytes: number;
  expires_in_hours: number;
}

export interface ExportHistory {
  id: string;
  file_name: string;
  file_type: string;
  record_count: number;
  r2_url: string;
  created_at: string;
}
