from __future__ import annotations

import time
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.core.logging import get_logger
from app.schemas.metadata import MetadataSignal
from app.schemas.visual import ElaForensicsResult, ElaPageMetrics, ElaPageResult, ForensicEvidence
from app.services.forensics import ela_config as cfg
from app.services.forensics.aggregation import aggregate_confidence, aggregate_page_scores
from app.services.forensics.artifacts import forensics_dir
from app.core.config import Settings

logger = get_logger(__name__)


def analyze_ela(
    *,
    analysis_id: str,
    document_type: str,
    file_type: str | None,
    page_images: list[tuple[int, Path]],
    settings: Settings,
) -> ElaForensicsResult:
    pages: list[ElaPageResult] = []
    for page_number, image_path in page_images:
        started = time.perf_counter()
        try:
            page = _analyze_page(
                analysis_id=analysis_id,
                page_number=page_number,
                image_path=image_path,
                document_type=document_type,
                file_type=file_type,
                settings=settings,
            )
            logger.info(
                "module=ela analysis_id=%s page=%s success duration_ms=%s score=%s quality_inputs=%s/%s",
                analysis_id,
                page_number,
                int((time.perf_counter() - started) * 1000),
                page.suspicion_score,
                file_type,
                document_type,
            )
            pages.append(page)
        except Exception:
            logger.exception("module=ela analysis_id=%s page=%s failure", analysis_id, page_number)
            pages.append(
                ElaPageResult(
                    page_number=page_number,
                    suspicion_score=0,
                    confidence=cfg.CONFIDENCE_MIN,
                    flagged=False,
                    metrics=ElaPageMetrics(mean_error=0.0, std_error=0.0, max_error=0.0, high_error_ratio=0.0),
                    limitations=["ELA could not be computed for this page. This is not evidence of tampering."],
                )
            )

    scores = [p.suspicion_score for p in pages]
    confidences = [p.confidence for p in pages]
    document_score = aggregate_page_scores(scores)
    document_conf = aggregate_confidence(confidences)
    quality = _document_quality(document_type, file_type, pages)
    flagged = document_score >= cfg.FLAG_THRESHOLD or any(p.flagged for p in pages)
    return ElaForensicsResult(
        layer="ela",
        suspicion_score=document_score,
        flagged=flagged,
        confidence=document_conf,
        analysis_quality=quality,
        pages=pages,
        summary=_summarize(pages, document_score, quality),
    )


def _document_quality(document_type: str, file_type: str | None, pages: list[ElaPageResult]) -> str:
    if document_type in {"native_pdf", "scanned_pdf"}:
        return "limited"
    if (file_type or "").lower() in {"png"}:
        return "limited"
    if (file_type or "").lower() in {"jpg", "jpeg"}:
        if any("globally elevated" in " ".join(p.limitations).lower() for p in pages):
            return "medium"
        return "high"
    return "medium"


def _summarize(pages: list[ElaPageResult], score: int, quality: str) -> str:
    if not pages:
        return "No pages were available for error level analysis."
    localized = any(
        any(s.id == "ela_localized_high_error" for s in p.signals) for p in pages
    )
    if localized:
        return (
            f"Potential manipulation signal detected: localized recompression inconsistency "
            f"(document ELA suspicion {score}/100, analysis quality {quality}). "
            "Bright ELA residuals are not proof of forgery."
        )
    if score == 0:
        return (
            f"No strong ELA anomaly evidence was detected (analysis quality {quality}). "
            "This does not establish authenticity."
        )
    return (
        f"ELA residuals were measured (suspicion {score}/100, analysis quality {quality}). "
        "Interpretation is limited when the source is PNG or a PDF raster; this is not proof of tampering."
    )


def _analyze_page(
    *,
    analysis_id: str,
    page_number: int,
    image_path: Path,
    document_type: str,
    file_type: str | None,
    settings: Settings,
) -> ElaPageResult:
    bgr, scale_note = _load_working_image(image_path)
    error = _error_map(bgr)
    mean = float(np.mean(error))
    std = float(np.std(error))
    max_error = float(np.max(error))
    thresh = max(
        float(np.percentile(error, cfg.HIGH_ERROR_PERCENTILE)),
        mean + cfg.HIGH_ERROR_SIGMA * std,
        cfg.HIGH_ERROR_FLOOR,
    )
    mask = (error >= thresh).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    high_ratio = float(mask.mean())
    components = _significant_components(mask, error)
    score, signals, uniform_noise = _score_page(mean, std, max_error, high_ratio, components, error.size)
    limitations = _limitations(document_type, file_type, uniform_noise, scale_note)
    confidence = _page_confidence(document_type, file_type, uniform_noise, bool(signals))
    flagged = score >= cfg.FLAG_THRESHOLD

    evidence_dir = forensics_dir(settings, analysis_id)
    heatmap_id = f"p{page_number:03d}_ela"
    _write_heatmap(error, evidence_dir / f"{heatmap_id}.png")
    evidence = [
        ForensicEvidence(
            type="ela_heatmap",
            artifact_id=heatmap_id,
            description="ELA residual visualization. Brighter areas indicate larger JPEG recompression error, not confirmed tampering.",
        )
    ]
    if components:
        overlay_id = f"p{page_number:03d}_ela_overlay"
        _write_overlay(bgr, components, evidence_dir / f"{overlay_id}.png")
        evidence.append(
            ForensicEvidence(
                type="ela_overlay",
                artifact_id=overlay_id,
                description="Regions where ELA residuals are locally concentrated relative to their surroundings.",
            )
        )

    return ElaPageResult(
        page_number=page_number,
        suspicion_score=score,
        confidence=confidence,
        flagged=flagged,
        metrics=ElaPageMetrics(
            mean_error=round(mean, 4),
            std_error=round(std, 4),
            max_error=round(max_error, 4),
            high_error_ratio=round(high_ratio, 6),
        ),
        evidence=evidence,
        signals=signals,
        limitations=limitations,
    )


def _load_working_image(path: Path) -> tuple[np.ndarray, str | None]:
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("unreadable_image")
    h, w = bgr.shape[:2]
    longest = max(h, w)
    if longest <= cfg.MAX_WORKING_SIDE:
        return bgr, None
    scale = cfg.MAX_WORKING_SIDE / longest
    work = cv2.resize(bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return work, f"ELA was computed on a {work.shape[1]}×{work.shape[0]} working copy; the original processing image was not overwritten."


def _error_map(bgr: np.ndarray) -> np.ndarray:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    buffer = BytesIO()
    pil.save(buffer, format="JPEG", quality=cfg.JPEG_QUALITY, subsampling=0)
    buffer.seek(0)
    recompressed = Image.open(buffer).convert("RGB")
    original = np.asarray(pil, dtype=np.int16)
    recomputed = np.asarray(recompressed, dtype=np.int16)
    diff = np.abs(original - recomputed).astype(np.float32)
    return diff.max(axis=2)


def _significant_components(mask: np.ndarray, error: np.ndarray) -> list[dict]:
    min_area = max(int(mask.size * cfg.MIN_COMPONENT_PIXEL_RATIO), 32)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    found: list[dict] = []
    for index in range(1, count):
        area = int(stats[index, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        x, y, w, h = (int(stats[index, cv2.CC_STAT_LEFT]), int(stats[index, cv2.CC_STAT_TOP]),
                      int(stats[index, cv2.CC_STAT_WIDTH]), int(stats[index, cv2.CC_STAT_HEIGHT]))
        component = labels == index
        local_mean = float(error[component].mean())
        dilated = cv2.dilate(component.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
        ring = (dilated == 1) & (~component)
        surround = float(error[ring].mean()) if ring.any() else float(error.mean())
        contrast = local_mean - surround
        if contrast < cfg.MIN_LOCAL_CONTRAST:
            continue
        found.append({"bbox": (x, y, w, h), "area": area, "contrast": contrast, "local_mean": local_mean})
        if len(found) >= cfg.MAX_COMPONENTS_TO_SCORE:
            break
    found.sort(key=lambda item: item["contrast"] * item["area"], reverse=True)
    return found


def _score_page(
    mean: float,
    std: float,
    max_error: float,
    high_ratio: float,
    components: list[dict],
    pixel_count: int,
) -> tuple[int, list[MetadataSignal], bool]:
    signals: list[MetadataSignal] = []
    score = 0
    # Many small high-error pixels with weak clusters → encoder/render noise.
    uniform_noise = high_ratio > 0.18 and len(components) <= 1 and (not components or components[0]["contrast"] < cfg.STRONG_LOCAL_CONTRAST)

    if components:
        top = components[0]
        area_ratio = top["area"] / max(pixel_count, 1)
        cluster_score = int(round(cfg.SCORE_LOCALIZED_CLUSTER * min(1.0, top["contrast"] / cfg.STRONG_LOCAL_CONTRAST) * min(1.0, area_ratio / 0.02)))
        cluster_score = max(8, cluster_score) if top["contrast"] >= cfg.MIN_LOCAL_CONTRAST else cluster_score
        score += cluster_score
        signals.append(
            MetadataSignal(
                id="ela_localized_high_error",
                finding="Region shows elevated recompression inconsistency.",
                severity="high" if top["contrast"] >= cfg.STRONG_LOCAL_CONTRAST else "medium",
                score_impact=cluster_score,
                detail=(
                    f"A residual cluster of {top['area']} px differs from its surroundings by "
                    f"{top['contrast']:.1f} ELA units. This is a potential manipulation signal, not proof."
                ),
            )
        )
        if len(components) >= 2:
            concentration = int(round(cfg.SCORE_CONCENTRATION * min(1.0, len(components) / 4)))
            score += concentration
            signals.append(
                MetadataSignal(
                    id="ela_error_concentration",
                    finding="Multiple localized ELA residual clusters were detected.",
                    severity="medium",
                    score_impact=concentration,
                    detail="Several spatially grouped high-error regions exist. Clustered residuals are more informative than a uniform noisy field.",
                )
            )

    if components:
        gap = components[0]["local_mean"] - mean
        if gap > 8:
            gap_score = int(round(cfg.SCORE_LOCAL_GLOBAL_GAP * min(1.0, gap / 20.0)))
            score += gap_score
            signals.append(
                MetadataSignal(
                    id="ela_local_global_gap",
                    finding="Local ELA residual exceeds the page-wide baseline.",
                    severity="medium",
                    score_impact=gap_score,
                    detail=f"The strongest cluster mean exceeds the page mean by {gap:.1f}. A global residual baseline is expected in JPEG/PDF rasters.",
                )
            )

    peak_score = int(round(cfg.SCORE_EXTREME_PEAK * min(1.0, max(0.0, max_error - mean - 3 * std) / 40.0)))
    if peak_score >= 4 and components:
        score += peak_score
        signals.append(
            MetadataSignal(
                id="ela_extreme_peak",
                finding="A sharp ELA residual peak is present inside a clustered region.",
                severity="low",
                score_impact=peak_score,
                detail="Isolated peaks without clustering are ignored; this peak coincides with a residual cluster.",
            )
        )

    if uniform_noise:
        score = max(0, score - cfg.SCORE_UNIFORM_NOISE_PENALTY)
        signals.append(
            MetadataSignal(
                id="ela_uniform_residual_field",
                finding="ELA residuals appear globally elevated rather than localized.",
                severity="low",
                score_impact=0,
                detail="A noisy residual field is common after JPEG encoding or PDF rasterization and is not treated as manipulation evidence.",
            )
        )

    return min(100, score), signals, uniform_noise


def _limitations(document_type: str, file_type: str | None, uniform_noise: bool, scale_note: str | None) -> list[str]:
    notes: list[str] = []
    if document_type in {"native_pdf", "scanned_pdf"}:
        notes.append("This page was rasterized from a PDF. ELA on rendered pages is limited and can reflect the renderer rather than prior JPEG edits.")
    if (file_type or "").lower() == "png":
        notes.append("Source is PNG. ELA is designed around JPEG recompression history, so confidence is reduced.")
    if (file_type or "").lower() in {"jpg", "jpeg"}:
        notes.append("ELA is more meaningful for JPEG inputs, but ordinary camera JPEGs also produce residual texture.")
    if uniform_noise:
        notes.append("Globally elevated residuals were observed; they are not classified as localized manipulation evidence.")
    if scale_note:
        notes.append(scale_note)
    notes.append("ELA does not prove that a document was forged.")
    return notes


def _page_confidence(document_type: str, file_type: str | None, uniform_noise: bool, has_signals: bool) -> float:
    if document_type in {"native_pdf", "scanned_pdf"}:
        value = cfg.CONFIDENCE_PDF_RENDER
    elif (file_type or "").lower() == "png":
        value = cfg.CONFIDENCE_PNG
    elif (file_type or "").lower() in {"jpg", "jpeg"}:
        value = cfg.CONFIDENCE_JPEG
    else:
        value = 0.4
    if uniform_noise:
        value -= cfg.CONFIDENCE_NOISY_DISCOUNT
    if not has_signals:
        value = min(value, 0.45)
    return round(min(cfg.CONFIDENCE_MAX, max(cfg.CONFIDENCE_MIN, value)), 2)


def _write_heatmap(error: np.ndarray, destination: Path) -> None:
    amplified = np.clip(error * cfg.VISUAL_AMPLIFY, 0, 255).astype(np.uint8)
    color = cv2.applyColorMap(amplified, cv2.COLORMAP_INFERNO)
    cv2.imwrite(str(destination), color)


def _write_overlay(bgr: np.ndarray, components: list[dict], destination: Path) -> None:
    overlay = bgr.copy()
    for item in components:
        x, y, w, h = item["bbox"]
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 180, 255), 2)
    blended = cv2.addWeighted(bgr, 0.65, overlay, 0.35, 0)
    for item in components:
        x, y, w, h = item["bbox"]
        cv2.rectangle(blended, (x, y), (x + w, y + h), (0, 180, 255), 2)
    cv2.imwrite(str(destination), blended)
