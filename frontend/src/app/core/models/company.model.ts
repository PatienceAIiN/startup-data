export interface Company {
  id: string;
  cin: string | null;
  company_name: string;
  company_status: string | null;
  roc_code: string | null;
  company_category: string | null;
  date_of_incorporation: string | null;
  state: string | null;
  authorised_capital: number | null;
  paid_up_capital: number | null;
  match_score: number;
  match_method: string | null;
  is_startup: boolean;
  registered_address: string | null;
  website: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  created_at: string;
}

export interface CompanyPage {
  items: Company[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface CompanyFilter {
  search?: string;
  state?: string;
  city?: string;
  status?: string;
  isStartup?: boolean;
  minScore?: number;
  page?: number;
  pageSize?: number;
}

export interface CompanyStats {
  total_companies: number;
  matched_companies: number;
  startups: number;
  avg_match_score: number;
  by_state: Record<string, number>;
  by_year: Record<number, number>;
  last_scrape: string | null;
}
