"""Collect overlay boxes only from computed forensic/intelligence geometry."""

from __future__ import annotations

from app.schemas.intelligence import DocumentIntelligenceResult
from app.schemas.signature import OverlayRegion, SignatureRegion
from app.schemas.visual import CopyMoveForensicsResult, ElaForensicsResult


def collect_overlays(
    *,
    copy_move: CopyMoveForensicsResult | None,
    ela: ElaForensicsResult | None,
    intelligence: DocumentIntelligenceResult | None,
    signatures: list[SignatureRegion],
) -> list[OverlayRegion]:
    regions: list[OverlayRegion] = []
    if copy_move:
        for page in copy_move.pages:
            for item in page.regions:
                regions.append(
                    OverlayRegion(
                        kind="copy_move",
                        label="Duplicated region",
                        page_number=page.page_number,
                        x=item.source_bbox.x,
                        y=item.source_bbox.y,
                        width=item.source_bbox.width,
                        height=item.source_bbox.height,
                        score=item.match_confidence,
                        explanation="Copy-move analysis located a geometrically verified duplicated region.",
                    )
                )
                regions.append(
                    OverlayRegion(
                        kind="copy_move",
                        label="Matched duplicate",
                        page_number=page.page_number,
                        x=item.matched_bbox.x,
                        y=item.matched_bbox.y,
                        width=item.matched_bbox.width,
                        height=item.matched_bbox.height,
                        score=item.match_confidence,
                        explanation="Corresponding duplicated region from copy-move matching.",
                    )
                )
    if intelligence:
        for check in intelligence.logical_checks:
            box = check.evidence.bbox
            if box is None or check.result not in {"fail", "warning"}:
                continue
            regions.append(
                OverlayRegion(
                    kind="text",
                    label=check.check_id.replace("_", " "),
                    page_number=check.evidence.page_number or 1,
                    x=box.x,
                    y=box.y,
                    width=box.width,
                    height=box.height,
                    score=check.confidence,
                    explanation=check.explanation,
                )
            )
    if ela and ela.flagged:
        pass
    for index, item in enumerate(signatures[:8]):
        regions.append(
            OverlayRegion(
                kind="signature",
                label=f"Signature candidate {index + 1}",
                page_number=item.page_number,
                x=item.x,
                y=item.y,
                width=item.width,
                height=item.height,
                score=item.score,
                explanation=item.reason or "Detected as a signature-like ink region.",
            )
        )
    return regions[:24]
