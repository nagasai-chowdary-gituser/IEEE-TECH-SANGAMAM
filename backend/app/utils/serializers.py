from app.models.document_analysis import AnalysisStatus, DocumentAnalysis
from app.schemas.analysis import AnalysisResponse, DocumentInfoPublic
from app.schemas.metadata import MetadataForensicsResult
from app.schemas.preprocessing import PreprocessingResultInternal, PreprocessingResultPublic
from app.schemas.ai import AIExplanation
from app.schemas.fusion import FusionResult
from app.schemas.intelligence import DocumentIntelligenceResult
from app.schemas.visual import (
    LAYERS_COMPLETED_MESSAGE,
    PIPELINE_MESSAGE,
    CopyMoveForensicsResult,
    ElaForensicsResult,
    VisualForensicsResult,
)


def shorten_sha256(value: str | None) -> str | None:
    if not value:
        return None
    return f"{value[:12]}…{value[-8:]}"


def public_preprocessing(raw_json: str | None) -> PreprocessingResultPublic | None:
    if not raw_json:
        return None
    internal = PreprocessingResultInternal.model_validate_json(raw_json)
    return PreprocessingResultPublic.from_internal(internal)


def public_metadata(raw_json: str | None) -> MetadataForensicsResult | None:
    if not raw_json:
        return None
    return MetadataForensicsResult.model_validate_json(raw_json)


def public_ela(raw_json: str | None) -> ElaForensicsResult | None:
    if not raw_json:
        return None
    return ElaForensicsResult.model_validate_json(raw_json)


def public_copy_move(raw_json: str | None) -> CopyMoveForensicsResult | None:
    if not raw_json:
        return None
    return CopyMoveForensicsResult.model_validate_json(raw_json)


def public_visual(raw_json: str | None) -> VisualForensicsResult | None:
    if not raw_json:
        return None
    return VisualForensicsResult.model_validate_json(raw_json)


def public_intelligence(raw_json: str | None) -> DocumentIntelligenceResult | None:
    if not raw_json:
        return None
    return DocumentIntelligenceResult.model_validate_json(raw_json)


def public_fusion(raw_json: str | None) -> FusionResult | None:
    if not raw_json:
        return None
    return FusionResult.model_validate_json(raw_json)


def public_explanation(raw_json: str | None) -> AIExplanation | None:
    if not raw_json:
        return None
    return AIExplanation.model_validate_json(raw_json)


def to_analysis_response(record: DocumentAnalysis) -> AnalysisResponse:
    ela = public_ela(record.ela_result_json)
    copy_move = public_copy_move(record.copy_move_result_json)
    visual = public_visual(record.visual_forensics_result_json)
    return AnalysisResponse(
        analysis_id=record.id,
        status=record.status,
        document=DocumentInfoPublic(
            original_filename=record.original_filename,
            file_type=record.file_type,
            document_type=record.document_type,
            file_size=record.file_size,
            sha256=record.sha256,
            sha256_short=shorten_sha256(record.sha256),
        ),
        preprocessing=public_preprocessing(record.preprocessing_result_json),
        metadata_forensics=public_metadata(record.metadata_result_json),
        ela=ela,
        copy_move=copy_move,
        visual_forensics=visual,
        document_intelligence=public_intelligence(record.document_intelligence_result_json),
        fusion=public_fusion(record.fusion_result_json),
        explanation=public_explanation(record.ai_explanation_json),
        pipeline_stage=record.pipeline_stage,
        pipeline_message=PIPELINE_MESSAGE if record.status != AnalysisStatus.FAILED else None,
        layers_completed=LAYERS_COMPLETED_MESSAGE if record.status != AnalysisStatus.FAILED else None,
        created_at=record.created_at,
        updated_at=record.updated_at,
        error_message=record.error_message,
    )
