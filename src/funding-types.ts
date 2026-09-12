export type Country = "SE" | "US";
export type Category =
  | "fundamental_aging"
  | "intervention"
  | "age_related_disease"
  | "care_research"
  | "other_aging_research"
  | "outside_scope"
  | "unresolved";
export type Review = {
  sample_size: number;
  reviewed: number;
  correct: number;
  accuracy: number | null;
  passed: boolean;
  top_awards_checked: number;
  top_awards_required: number;
  report_approved: boolean;
  publication_ready: boolean;
};
export type Summary = {
  records: number;
  category_counts: Record<Category, number>;
  category_amount_minor: Record<Category, number>;
  known_amount_minor: number;
  missing_amount_records: number;
  zero_amount_records: number;
  numerator_minor: number;
  denominator_minor: number;
  unresolved_minor: number;
  outside_scope_minor: number;
  ratio: number | null;
  biology_only_ratio: number | null;
  sensitivity_lower: number | null;
  sensitivity_upper: number | null;
  unresolved_known_money_share: number | null;
  range_note: string;
};
export type Report = {
  country: Country;
  name: string;
  currency: string;
  label: string;
  period: string;
  basis: string;
  version_hash: string;
  publication_ready: boolean;
  record_count: number;
  missing_amount_records: number;
  zero_amount_records: number;
  summary: Summary | null;
  review: Review;
  coverage: {
    complete: boolean;
    api_rows?: number;
    excluded_subprojects?: number;
    funders?: {
      funder_id: string;
      api_rows_all_years: number;
      selected_funding_year_rows: number;
    }[];
  };
};
export type Release = {
  release_id: string;
  year: number;
  method_version: string;
  categories: Record<Category, string>;
  reports: Record<Country, Report>;
  review: {
    target: number;
    overall: Review;
    countries: Record<Country, Review>;
    sampling_note: string;
    benchmark_created_at: string;
  };
  ledger_hash: string;
  source_count: number;
  scope_note: string;
  financial_note: string;
  calculation: string;
  source_checked_at: string;
  research_crosschecks: {
    attempted_requests_total: number;
    combined_cap: number;
    checked_at: string;
    checks: {
      provider: string;
      query: string;
      status: string;
      checked_at: string;
      links: { title: string; url: string }[];
    }[];
  };
};
export type Grant = {
  id: string;
  country: Country;
  source: string;
  source_id: string;
  project_number: string;
  title: string;
  funder: string;
  funder_id: string;
  government_funder: boolean;
  year: number;
  currency: string;
  amount_minor: number | null;
  amount_basis: string;
  funding_start: string | null;
  funding_end: string | null;
  source_date: string | null;
  source_date_note: string;
  source_url: string;
  retrieved_at: string;
  source_hash: string;
  version_hash: string;
  source_location: string;
  classification: {
    category: Category;
    method: string;
    rationale: string;
    supporting_passage: string;
    human_verified: boolean;
  } | null;
};
