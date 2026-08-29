export type AnalysisStatus =
  | "PENDING"
  | "PROCESSING"
  | "PARTIAL_COMPLETE"
  | "COMPLETE"
  | "FAILED";

export interface DocumentInfo {
  original_filename: string;
  file_type: string | null;
  document_type: string | null;
  file_size: number | null;
  sha256: string | null;
  sha256_short: string | null;
}

export interface PageInfo {
  page_number: number;
  width: number;
  height: number;
}

export interface PreprocessingResult {
  document_type: string;
  page_count: number;
  pages: PageInfo[];
  processing_notes: string[];
  pdf_info: Record<string, unknown> | null;
  image_format: string | null;
}

export interface MetadataSignal {
  id: string;
  finding: string;
  severity: "low" | "medium" | "high";
  score_impact: number;
  detail: string;
}

export interface MetadataForensicsResult {
  layer: string;
  suspicion_score: number;
  flagged: boolean;
  confidence: number;
  signals: MetadataSignal[];
  summary: string;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ForensicEvidence {
  type: string;
  artifact_id: string;
  description: string;
}

export interface ElaPageMetrics {
  mean_error: number;
  std_error: number;
  max_error: number;
  high_error_ratio: number;
}

export interface ElaPageResult {
  page_number: number;
  suspicion_score: number;
  confidence: number;
  flagged: boolean;
  metrics: ElaPageMetrics;
  evidence: ForensicEvidence[];
  signals: MetadataSignal[];
  limitations: string[];
}

export interface ElaForensicsResult {
  layer: string;
  suspicion_score: number;
  flagged: boolean;
  confidence: number;
  analysis_quality: "high" | "medium" | "limited";
  pages: ElaPageResult[];
  summary: string;
  module_error: string | null;
}

export interface CopyMovePageMetrics {
  keypoints_detected: number;
  raw_matches: number;
  filtered_matches: number;
  geometrically_verified_matches: number;
  suspicious_clusters: number;
}

export interface CopyMoveRegion {
  region_id: string;
  source_bbox: BoundingBox;
  matched_bbox: BoundingBox;
  match_confidence: number;
  evidence_strength: "low" | "medium" | "high";
}

export interface CopyMovePageResult {
  page_number: number;
  suspicion_score: number;
  confidence: number;
  flagged: boolean;
  metrics: CopyMovePageMetrics;
  regions: CopyMoveRegion[];
  evidence: ForensicEvidence[];
  signals: MetadataSignal[];
  limitations: string[];
}

export interface CopyMoveForensicsResult {
  layer: string;
  suspicion_score: number;
  flagged: boolean;
  confidence: number;
  pages: CopyMovePageResult[];
  summary: string;
  module_error: string | null;
}

export interface VisualForensicsResult {
  layer: string;
  ela: ElaForensicsResult | null;
  copy_move: CopyMoveForensicsResult | null;
  pipeline_message: string;
}

export interface TextToken {
  text: string;
  bbox: BoundingBox | null;
  confidence: number;
  font_size: number | null;
}

export interface ExtractedPage {
  page_number: number;
  source: "native_pdf" | "ocr";
  quality: "high" | "medium" | "low" | "failed";
  confidence: number;
  text: string;
  tokens: TextToken[];
  limitations: string[];
}

export interface ExtractionResult {
  overall_quality: "high" | "medium" | "low" | "failed";
  overall_confidence: number;
  pages: ExtractedPage[];
  tesseract_available: boolean;
  notes: string[];
}

export interface FieldEvidence {
  label: string | null;
  bbox: BoundingBox | null;
  snippet: string | null;
}

export interface ExtractedField {
  field_id: string;
  field_type: string;
  value: string;
  normalized_value: unknown;
  page_number: number | null;
  confidence: number;
  source: string;
  evidence: FieldEvidence | null;
}

export interface CheckEvidence {
  expected: unknown;
  observed: unknown;
  bbox: BoundingBox | null;
  page_number: number | null;
  extra: Record<string, unknown>;
}

export interface LogicalCheck {
  check_id: string;
  category: string;
  result: "pass" | "warning" | "fail" | "not_applicable" | "insufficient_data";
  severity: "low" | "medium" | "high";
  score_impact: number;
  confidence: number;
  evidence: CheckEvidence;
  explanation: string;
  artifact_id: string | null;
}

export interface BarcodeFinding {
  kind: string;
  value: string;
  page_number: number;
  bbox: BoundingBox | null;
}

export interface DocumentClassification {
  document_class: "invoice" | "certificate" | "generic_document";
  confidence: number;
  rationale: string;
}

export interface DocumentIntelligenceResult {
  layer: string;
  extraction: ExtractionResult;
  classification: DocumentClassification;
  fields: ExtractedField[];
  logical_checks: LogicalCheck[];
  barcodes: BarcodeFinding[];
  suspicion_score: number;
  flagged: boolean;
  confidence: number;
  summary: string;
  limitations: string[];
  module_error: string | null;
}

export interface FusionLayerContribution {
  layer: "metadata" | "ela" | "copy_move" | "document_intelligence";
  raw_score: number;
  reliability: number;
  effective_contribution: number;
  status: "available" | "limited" | "failed" | "unavailable";
  summary: string;
}

export interface FusionCorroboration {
  independent_layers_with_evidence: FusionLayerContribution["layer"][];
  strength: "none" | "weak" | "moderate" | "strong";
  description: string;
}

export interface FusionTopFinding {
  rank: number;
  layer: FusionLayerContribution["layer"];
  finding: string;
  severity: "low" | "medium" | "high";
  confidence: number;
  evidence_reference: string | null;
}

export interface FusionResult {
  layer: string;
  overall_risk_score: number;
  risk_level: "LOW" | "MODERATE" | "ELEVATED" | "HIGH" | "INCONCLUSIVE";
  assessment_confidence: number;
  analysis_coverage: number;
  layer_contributions: FusionLayerContribution[];
  corroboration: FusionCorroboration;
  top_findings: FusionTopFinding[];
  limitations: string[];
  assessment_summary: string;
  recommended_action:
    | "NO_ADDITIONAL_ACTION"
    | "MANUAL_REVIEW_RECOMMENDED"
    | "PRIORITY_MANUAL_REVIEW"
    | "REANALYZE_WITH_HIGHER_QUALITY_SOURCE";
}

export interface AIExplanation {
  summary: string;
  risk_explanation: string;
  strongest_evidence: { layer: string; explanation: string }[];
  corroboration_explanation: string;
  limitations_explanation: string;
  recommended_next_step: string;
  disclaimer: string;
  source: "ai" | "deterministic_fallback";
}

export interface AskResponse {
  answer: string;
  grounding: {
    risk_level: FusionResult["risk_level"] | null;
    referenced_layers: string[];
  };
  source: "ai" | "deterministic_fallback";
}

export interface AnalysisSummaryItem {
  analysis_id: string;
  original_filename: string;
  document_type: string | null;
  status: AnalysisStatus;
  risk_level: string | null;
  overall_risk_score: number | null;
  pipeline_stage: string | null;
  created_at: string;
}

export interface AnalysisListResponse {
  items: AnalysisSummaryItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface AnalysisResponse {
  analysis_id: string;
  status: AnalysisStatus;
  document: DocumentInfo;
  preprocessing: PreprocessingResult | null;
  metadata_forensics: MetadataForensicsResult | null;
  ela: ElaForensicsResult | null;
  copy_move: CopyMoveForensicsResult | null;
  visual_forensics: VisualForensicsResult | null;
  document_intelligence: DocumentIntelligenceResult | null;
  fusion: FusionResult | null;
  explanation: AIExplanation | null;
  pipeline_stage: string | null;
  pipeline_message: string | null;
  layers_completed: string | null;
  created_at: string;
  updated_at: string;
  error_message: string | null;
}

export interface HealthResponse {
  status: string;
  service: string;
  environment: string;
  database: string;
}
