from __future__ import annotations

from typing import Any

from app.models.document_analysis import DocumentAnalysis
from app.utils.serializers import (
    public_copy_move,
    public_ela,
    public_fusion,
    public_intelligence,
    public_metadata,
    public_preprocessing,
)


def build_analysis_context(record: DocumentAnalysis) -> dict[str, Any]:
    """Compact, path-free context for the explanation model."""
    preprocessing = public_preprocessing(record.preprocessing_result_json)
    metadata = public_metadata(record.metadata_result_json)
    ela = public_ela(record.ela_result_json)
    copy_move = public_copy_move(record.copy_move_result_json)
    intelligence = public_intelligence(record.document_intelligence_result_json)
    fusion = public_fusion(record.fusion_result_json)

    context: dict[str, Any] = {
        "document": {
            "filename": record.original_filename,
            "type": record.document_type,
            "file_type": record.file_type,
            "page_count": preprocessing.page_count if preprocessing else None,
            "sha256_short": _short_hash(record.sha256),
        },
        "assessment": None,
        "top_findings": [],
        "metadata": None,
        "visual_forensics": {
            "ela_summary": None,
            "ela_status": "unavailable" if ela is None else ("failed" if ela.module_error else "available"),
            "copy_move_summary": None,
            "copy_move_status": "unavailable" if copy_move is None else ("failed" if copy_move.module_error else "available"),
        },
        "document_intelligence": None,
        "limitations": [],
        "corroboration": None,
    }

    if fusion:
        context["assessment"] = {
            "risk_level": fusion.risk_level,
            "overall_risk_score": fusion.overall_risk_score,
            "assessment_confidence": fusion.assessment_confidence,
            "analysis_coverage": fusion.analysis_coverage,
            "recommended_action": fusion.recommended_action,
            "assessment_summary": fusion.assessment_summary,
        }
        context["top_findings"] = [
            {
                "rank": item.rank,
                "layer": item.layer,
                "finding": item.finding,
                "severity": item.severity,
                "confidence": item.confidence,
            }
            for item in fusion.top_findings
        ]
        context["limitations"] = list(fusion.limitations)
        context["corroboration"] = {
            "independent_layers_with_evidence": fusion.corroboration.independent_layers_with_evidence,
            "strength": fusion.corroboration.strength,
            "description": fusion.corroboration.description,
        }
        context["layer_contributions"] = [
            {
                "layer": row.layer,
                "raw_score": row.raw_score,
                "reliability": row.reliability,
                "status": row.status,
                "summary": row.summary,
            }
            for row in fusion.layer_contributions
        ]

    if metadata:
        context["metadata"] = {
            "summary": metadata.summary,
            "suspicion_score": metadata.suspicion_score,
            "confidence": metadata.confidence,
            "signals": [
                {"id": s.id, "finding": s.finding, "severity": s.severity}
                for s in metadata.signals[:12]
            ],
        }

    if ela:
        context["visual_forensics"]["ela_summary"] = ela.summary
        context["visual_forensics"]["ela_suspicion_score"] = ela.suspicion_score
        context["visual_forensics"]["ela_analysis_quality"] = ela.analysis_quality
        if ela.module_error:
            context["visual_forensics"]["ela_error"] = "ELA analysis did not complete."

    if copy_move:
        context["visual_forensics"]["copy_move_summary"] = copy_move.summary
        context["visual_forensics"]["copy_move_suspicion_score"] = copy_move.suspicion_score
        if copy_move.module_error:
            context["visual_forensics"]["copy_move_error"] = "Copy-move analysis did not complete."

    if intelligence:
        failing = [
            {
                "check_id": check.check_id,
                "result": check.result,
                "severity": check.severity,
                "explanation": check.explanation,
            }
            for check in intelligence.logical_checks
            if check.result in {"fail", "warning"}
        ]
        context["document_intelligence"] = {
            "summary": intelligence.summary,
            "suspicion_score": intelligence.suspicion_score,
            "extraction_quality": intelligence.extraction.overall_quality,
            "logical_checks": failing[:12],
            "limitations": list(intelligence.limitations[:8]),
            "status": "failed" if intelligence.module_error else "available",
        }

    serialized = _reject_secrets(context)
    return serialized


def _short_hash(value: str | None) -> str | None:
    if not value:
        return None
    return f"{value[:12]}…{value[-8:]}"


def _reject_secrets(payload: Any) -> Any:
    """Drop keys that look like paths, secrets, or traces if they ever appear."""
    blocked = {
        "file_path",
        "path",
        "api_key",
        "ai_api_key",
        "database_url",
        "traceback",
        "stack",
        "password",
        "secret",
        "tesseract_cmd",
    }
    if isinstance(payload, dict):
        cleaned = {}
        for key, value in payload.items():
            lowered = str(key).lower()
            if lowered in blocked or "api_key" in lowered:
                continue
            if isinstance(value, str) and _looks_like_path(value):
                continue
            cleaned[key] = _reject_secrets(value)
        return cleaned
    if isinstance(payload, list):
        return [_reject_secrets(item) for item in payload]
    return payload


def _looks_like_path(value: str) -> bool:
    if "\\users\\" in value.lower() or value.startswith("/") and "/processed/" in value.replace("\\", "/"):
        return True
    if ":\\" in value or value.startswith("\\\\"):
        return True
    return False
