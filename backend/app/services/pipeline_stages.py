from __future__ import annotations

STAGE_SECURING = "securing_document"
STAGE_PREPROCESSING = "preprocessing"
STAGE_METADATA = "metadata_analysis"
STAGE_VISUAL = "visual_forensics"
STAGE_INTELLIGENCE = "document_intelligence"
STAGE_FUSION = "evidence_fusion"
STAGE_EXPLANATION = "preparing_explanation"
STAGE_COMPLETE = "complete"
STAGE_FAILED = "failed"

STAGE_LABELS = {
    STAGE_SECURING: "Securing document",
    STAGE_PREPROCESSING: "Preprocessing",
    STAGE_METADATA: "Metadata analysis",
    STAGE_VISUAL: "Visual forensics",
    STAGE_INTELLIGENCE: "Document intelligence",
    STAGE_FUSION: "Evidence fusion",
    STAGE_EXPLANATION: "Preparing explanation",
    STAGE_COMPLETE: "Complete",
    STAGE_FAILED: "Failed",
}
