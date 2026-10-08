export interface ModuleStats {
  total: number;
  by_status: Record<string, number>;
  by_outcome: Record<string, number>;
}

export interface AiUsageWindow {
  calls: number;
  cached: number;
  rate_limited: number;
  failures: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
}

export interface AiSubjectUsage {
  subject: string;
  calls: number;
  tokens: number;
  estimated_cost_usd: number;
}

export interface AiBlock {
  id: string;
  subject: string;
  reason: string;
  blocked_until: string;
}

export interface RecentActivity {
  module: "forensics" | "compliance" | "certificate";
  id: string;
  original_filename: string;
  status: string;
  outcome: string | null;
  created_at: string;
}

export interface ServiceConfig {
  ai_explanations: boolean;
  pan_verification: boolean;
  gst_verification: boolean;
  google_sign_in: boolean;
  google_admin_emails: number;
  default_passwords_in_use: boolean;
}

export interface AdminOverview {
  forensics: ModuleStats;
  compliance: ModuleStats;
  certificates: ModuleStats;
  ai_usage: {
    last_24h: AiUsageWindow;
    all_time: AiUsageWindow;
    top_subjects_24h: AiSubjectUsage[];
    active_blocks: AiBlock[];
  };
  recent_activity: RecentActivity[];
  services: ServiceConfig;
}
