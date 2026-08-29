from __future__ import annotations

import time
from pathlib import Path

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.preprocessing import PreprocessingResultInternal
from app.schemas.visual import PIPELINE_MESSAGE, CopyMoveForensicsResult, ElaForensicsResult, VisualForensicsResult
from app.services.forensics.copy_move_forensics import analyze_copy_move
from app.services.forensics.ela_forensics import analyze_ela

logger = get_logger(__name__)


def run_visual_forensics(
    *,
    analysis_id: str,
    document_type: str,
    file_type: str | None,
    preprocessing: PreprocessingResultInternal,
    settings: Settings,
) -> VisualForensicsResult:
    pages = [(item.page_number, Path(item.path)) for item in preprocessing.page_images]
    ela: ElaForensicsResult | None = None
    copy_move: CopyMoveForensicsResult | None = None

    started = time.perf_counter()
    try:
        ela = analyze_ela(
            analysis_id=analysis_id,
            document_type=document_type,
            file_type=file_type,
            page_images=pages,
            settings=settings,
        )
        logger.info(
            "module=ela analysis_id=%s success duration_ms=%s score=%s",
            analysis_id,
            int((time.perf_counter() - started) * 1000),
            ela.suspicion_score,
        )
    except Exception as exc:
        logger.exception("module=ela analysis_id=%s failure reason=%s", analysis_id, type(exc).__name__)
        ela = ElaForensicsResult(
            layer="ela",
            suspicion_score=0,
            flagged=False,
            confidence=0.0,
            analysis_quality="limited",
            pages=[],
            summary="ELA did not complete. Module failure is not evidence of tampering.",
            module_error="ELA module failed while processing this document.",
        )

    copy_started = time.perf_counter()
    try:
        copy_move = analyze_copy_move(
            analysis_id=analysis_id,
            page_images=pages,
            settings=settings,
        )
        logger.info(
            "module=copy_move analysis_id=%s success duration_ms=%s score=%s",
            analysis_id,
            int((time.perf_counter() - copy_started) * 1000),
            copy_move.suspicion_score,
        )
    except Exception as exc:
        logger.exception("module=copy_move analysis_id=%s failure reason=%s", analysis_id, type(exc).__name__)
        copy_move = CopyMoveForensicsResult(
            layer="copy_move",
            suspicion_score=0,
            flagged=False,
            confidence=0.0,
            pages=[],
            summary="Copy-move analysis did not complete. Module failure is not evidence of tampering.",
            module_error="Copy-move module failed while processing this document.",
        )

    return VisualForensicsResult(
        layer="visual",
        ela=ela,
        copy_move=copy_move,
        pipeline_message=PIPELINE_MESSAGE,
    )
