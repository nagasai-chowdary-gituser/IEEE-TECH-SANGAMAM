export type VerificationOutcome =
  | "not_extracted"
  | "format_invalid"
  | "skipped"
  | "passed"
  | "failed"
  | "unavailable"
  | "error";

export type OverallCompliance = "COMPLIANT" | "REVIEW_REQUIRED" | "HIGH_RISK" | "INCONCLUSIVE";

export interface ExtractedIdentifier {
  kind: "pan" | "gstin";
  value: string | null;
  format_status: "valid" | "invalid" | "not_extracted";
  confidence: number | null;
  source_page: number | null;
  snippet: string | null;
}

export interface CertificateFields {
  pan: ExtractedIdentifier;
  gstin: ExtractedIdentifier;
  udyam_number: string | null;
  enterprise_name: string | null;
  registration_date: string | null;
  limitations: string[];
}

export interface IdentifierVerification {
  kind: "pan" | "gstin";
  extracted_value: string | null;
  format_status: "valid" | "invalid" | "not_extracted";
  outcome: VerificationOutcome;
  provider_status: string | null;
  details: Record<string, unknown>;
  verified_at: string | null;
  limitation: string | null;
}

export interface IntegrityAssessment {
  level: string;
  forensic_risk_level: string | null;
  overall_risk_score: number | null;
  assessment_confidence: number | null;
  analysis_coverage: number | null;
  forensic_analysis_id: string | null;
  top_findings: string[];
  limitations: string[];
  summary: string;
}

export interface ComplianceAggregation {
  overall_status: OverallCompliance;
  compliance_risk_score: number;
  assessment_summary: string;
  recommended_action: string;
  limitations: string[];
  pan: IdentifierVerification;
  gstin: IdentifierVerification;
  integrity: IntegrityAssessment;
}

export interface ComplianceResponse {
  compliance_id: string;
  forensic_analysis_id: string | null;
  status: string;
  pipeline_stage: string | null;
  original_filename: string;
  file_type: string | null;
  file_size: number | null;
  sha256_short: string | null;
  certificate_fields: CertificateFields | null;
  pan: IdentifierVerification | null;
  gstin: IdentifierVerification | null;
  integrity: IntegrityAssessment | null;
  aggregation: ComplianceAggregation | null;
  overall_status: OverallCompliance | null;
  compliance_risk_score: number | null;
  forensic_status: string | null;
  created_at: string;
  updated_at: string;
  error_message: string | null;
}

export interface ComplianceSummaryItem {
  compliance_id: string;
  original_filename: string;
  enterprise_name: string | null;
  overall_status: string | null;
  pan_outcome: string | null;
  gstin_outcome: string | null;
  integrity_level: string | null;
  created_at: string;
}

export interface ComplianceListResponse {
  items: ComplianceSummaryItem[];
  total: number;
  limit: number;
  offset: number;
}
