from datetime import datetime

from pydantic import BaseModel

from app.models.document_analysis import AnalysisStatus
from app.schemas.metadata import MetadataForensicsResult
from app.schemas.preprocessing import PreprocessingResultPublic
from app.schemas.visual import (
    LAYERS_COMPLETED_MESSAGE,
    PIPELINE_MESSAGE,
    CopyMoveForensicsResult,
    ElaForensicsResult,
    VisualForensicsResult,
)
from app.schemas.ai import AIExplanation
from app.schemas.fusion import FusionResult
from app.schemas.intelligence import DocumentIntelligenceResult


class DocumentInfoPublic(BaseModel):
    original_filename: str
    file_type: str | None = None
    document_type: str | None = None
    file_size: int | None = None
    sha256: str | None = None
    sha256_short: str | None = None


class AnalysisResponse(BaseModel):
    analysis_id: str
    status: AnalysisStatus
    document: DocumentInfoPublic
    preprocessing: PreprocessingResultPublic | None = None
    metadata_forensics: MetadataForensicsResult | None = None
    ela: ElaForensicsResult | None = None
    copy_move: CopyMoveForensicsResult | None = None
    visual_forensics: VisualForensicsResult | None = None
    document_intelligence: DocumentIntelligenceResult | None = None
    fusion: FusionResult | None = None
    explanation: AIExplanation | None = None
    pipeline_stage: str | None = None
    pipeline_message: str | None = PIPELINE_MESSAGE
    layers_completed: str | None = LAYERS_COMPLETED_MESSAGE
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    database: str
