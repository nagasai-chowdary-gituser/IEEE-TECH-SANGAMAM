from __future__ import annotations

from app.schemas.fusion import FusionResult
from app.schemas.intelligence import DocumentIntelligenceResult
from app.schemas.metadata import MetadataForensicsResult
from app.schemas.visual import CopyMoveForensicsResult, ElaForensicsResult
from app.services.fusion.confidence_model import apply_reliability_from_results
from app.services.fusion.fusion_engine import fuse


def run_fusion(
    metadata: MetadataForensicsResult | None,
    ela: ElaForensicsResult | None,
    copy_move: CopyMoveForensicsResult | None,
    intelligence: DocumentIntelligenceResult | None,
) -> FusionResult:
    layers = apply_reliability_from_results(metadata, ela, copy_move, intelligence)
    return fuse(layers)
