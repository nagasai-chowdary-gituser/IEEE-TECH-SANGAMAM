export type ComparisonStatus =
  | "REFERENCE_MATCH_HIGH"
  | "REFERENCE_MATCH_MODERATE"
  | "POTENTIAL_MISMATCH"
  | "INCONCLUSIVE";

export interface SignatureRegion {
  page_number: number;
  x: number;
  y: number;
  width: number;
  height: number;
  score: number | null;
  source: "auto" | "manual";
  reason: string | null;
}

export interface SignatureQuality {
  score: number;
  width: number;
  height: number;
  ink_ratio: number;
  sharpness: number;
  limitations: string[];
}

export interface ComparisonSignals {
  structural_similarity: number | null;
  contour_similarity: number | null;
  feature_match_score: number | null;
  geometry_similarity: number | null;
  histogram_similarity: number | null;
  image_quality_score: number | null;
  region_detection_confidence: number | null;
  unavailable: string[];
}

export interface SignatureFusion {
  overall_status: ComparisonStatus;
  similarity_score: number;
  assessment_confidence: number;
  assessment_summary: string;
  recommended_action: string;
  limitations: string[];
  signals: ComparisonSignals;
}

export interface CombinedSignatureAssessment {
  overall_concern: "LOW_CONCERN" | "REVIEW_REQUIRED" | "ELEVATED_CONCERN" | "INCONCLUSIVE";
  summary: string;
  comparison_status: ComparisonStatus;
  tamper_level: string | null;
  final_score: number | null;
  originality_score: number | null;
  originality_verdict: "SAFE" | "NOT_SAFE" | "REVIEW" | "UNAVAILABLE" | null;
  overall_verdict: "SAFE" | "NOT_SAFE" | "REVIEW" | null;
}

export interface OverlayRegion {
  kind: "text" | "copy_move" | "compression" | "signature" | "suspicious";
  label: string;
  page_number: number;
  x: number;
  y: number;
  width: number;
  height: number;
  score: number | null;
  explanation: string;
}

export interface CertificateField {
  field_id: string;
  label: string;
  value: string;
  confidence: number | null;
  source: string | null;
}

export interface RankedFinding {
  rank: number;
  stream: "document" | "signature" | "reference";
  finding: string;
  strength: "low" | "moderate" | "high";
}

export interface StreamAssessment {
  status: string;
  summary: string;
  confidence: number | null;
  risk_score: number | null;
  findings: string[];
  limitations: string[];
}

export interface CertificateIntegrityAssessment {
  overall_status: "CERTIFICATE_CLEAR" | "REVIEW_REQUIRED" | "ELEVATED_CONCERN" | "HIGH_MANIPULATION_CONCERN" | "INCONCLUSIVE";
  confidence: number;
  analysis_coverage: number;
  summary: string;
  recommended_action: string;
  completed_checks: string[];
  unavailable_checks: string[];
  limitations: string[];
  top_findings: RankedFinding[];
  document_content: StreamAssessment;
  signature_integrity: StreamAssessment;
  reference_comparison: StreamAssessment | null;
  extracted_fields: CertificateField[];
  overlay_regions: OverlayRegion[];
}

export interface ReferenceSignature {
  reference_id: string;
  label: string | null;
  original_filename: string;
  file_type: string;
  file_size: number;
  width: number | null;
  height: number | null;
  quality_score: number | null;
  created_at: string;
}

export interface SignatureComparisonResponse {
  comparison_id: string;
  reference_id: string | null;
  reference_label: string | null;
  forensic_analysis_id: string | null;
  status: string;
  pipeline_stage: string | null;
  original_filename: string;
  file_type: string | null;
  file_size: number | null;
  sha256_short: string | null;
  candidates: SignatureRegion[];
  selected_region: SignatureRegion | null;
  document_quality: SignatureQuality | null;
  reference_quality: SignatureQuality | null;
  signals: ComparisonSignals | null;
  fusion: SignatureFusion | null;
  tamper: { level?: string; summary?: string; top_findings?: string[] } | null;
  combined: CombinedSignatureAssessment | null;
  certificate: CertificateIntegrityAssessment | null;
  overall_status: string | null;
  artifacts: Record<string, string>;
  forensic_status: string | null;
  created_at: string;
  updated_at: string;
  error_message: string | null;
}

export interface SignatureComparisonSummary {
  comparison_id: string;
  original_filename: string;
  reference_label: string | null;
  overall_status: string | null;
  certificate_status: string | null;
  tamper_level: string | null;
  final_score: number | null;
  originality_score: number | null;
  originality_verdict: "SAFE" | "NOT_SAFE" | "REVIEW" | "UNAVAILABLE" | null;
  overall_verdict: "SAFE" | "NOT_SAFE" | "REVIEW" | null;
  created_at: string;
}

export interface SignatureComparisonListResponse {
  items: SignatureComparisonSummary[];
  total: number;
  limit: number;
  offset: number;
}
