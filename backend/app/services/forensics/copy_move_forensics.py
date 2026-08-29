from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.metadata import MetadataSignal
from app.schemas.visual import (
    BoundingBox,
    CopyMoveForensicsResult,
    CopyMovePageMetrics,
    CopyMovePageResult,
    CopyMoveRegion,
    ForensicEvidence,
)
from app.services.forensics import copy_move_config as cfg
from app.services.forensics.aggregation import aggregate_confidence, aggregate_page_scores
from app.services.forensics.artifacts import forensics_dir

logger = get_logger(__name__)


def analyze_copy_move(
    *,
    analysis_id: str,
    page_images: list[tuple[int, Path]],
    settings: Settings,
) -> CopyMoveForensicsResult:
    pages: list[CopyMovePageResult] = []
    for page_number, image_path in page_images:
        started = time.perf_counter()
        try:
            page = _analyze_page(analysis_id, page_number, image_path, settings)
            logger.info(
                "module=copy_move analysis_id=%s page=%s success duration_ms=%s score=%s inliers=%s",
                analysis_id,
                page_number,
                int((time.perf_counter() - started) * 1000),
                page.suspicion_score,
                page.metrics.geometrically_verified_matches,
            )
            pages.append(page)
        except Exception:
            logger.exception("module=copy_move analysis_id=%s page=%s failure", analysis_id, page_number)
            pages.append(
                CopyMovePageResult(
                    page_number=page_number,
                    suspicion_score=0,
                    confidence=cfg.CONFIDENCE_BASE,
                    flagged=False,
                    metrics=CopyMovePageMetrics(
                        keypoints_detected=0,
                        raw_matches=0,
                        filtered_matches=0,
                        geometrically_verified_matches=0,
                        suspicious_clusters=0,
                    ),
                    limitations=["Copy-move analysis could not be completed for this page. Failure is not evidence of tampering."],
                )
            )

    scores = [p.suspicion_score for p in pages]
    document_score = aggregate_page_scores(scores)
    document_conf = aggregate_confidence([p.confidence for p in pages])
    flagged = document_score >= cfg.FLAG_THRESHOLD or any(p.flagged for p in pages)
    return CopyMoveForensicsResult(
        layer="copy_move",
        suspicion_score=document_score,
        flagged=flagged,
        confidence=document_conf,
        pages=pages,
        summary=_summarize(pages, document_score),
    )


def _summarize(pages: list[CopyMovePageResult], score: int) -> str:
    regions = sum(len(p.regions) for p in pages)
    if regions == 0:
        return (
            "No strong duplicated-region evidence was detected. Repeated letters, borders, and template "
            "elements are filtered and are not treated as copy-move proof."
        )
    return (
        f"Repeated visual pattern detected in {regions} geometrically consistent region pair(s) "
        f"(document suspicion {score}/100). Copy-move signals are not legal proof of forgery."
    )


def _analyze_page(analysis_id: str, page_number: int, image_path: Path, settings: Settings) -> CopyMovePageResult:
    original = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if original is None:
        raise ValueError("unreadable_image")
    work, scale, resized = _working_image(original)
    gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=cfg.ORB_FEATURES, scaleFactor=1.2, nlevels=8)
    keypoints, descriptors = orb.detectAndCompute(gray, None)
    keypoint_count = 0 if keypoints is None else len(keypoints)
    limitations: list[str] = []
    if resized:
        limitations.append(
            f"Feature extraction used a {work.shape[1]}×{work.shape[0]} working copy. Bounding boxes are mapped back to the processing image."
        )

    empty_metrics = CopyMovePageMetrics(
        keypoints_detected=keypoint_count,
        raw_matches=0,
        filtered_matches=0,
        geometrically_verified_matches=0,
        suspicious_clusters=0,
    )
    if descriptors is None or keypoint_count < 20:
        limitations.append("Too few keypoints were detected for reliable copy-move analysis.")
        return CopyMovePageResult(
            page_number=page_number,
            suspicion_score=0,
            confidence=cfg.CONFIDENCE_BASE,
            flagged=False,
            metrics=empty_metrics,
            limitations=limitations + ["Copy-move detection does not prove authenticity or forgery."],
        )

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    knn = matcher.knnMatch(descriptors, descriptors, k=3)
    raw_matches = 0
    filtered: list[tuple[cv2.DMatch, tuple[float, float], tuple[float, float]]] = []
    for pair in knn:
        # First neighbor is typically the keypoint itself when matching an image to itself.
        candidates = [match for match in pair if match.queryIdx != match.trainIdx]
        if len(candidates) < 2:
            continue
        best, second = candidates[0], candidates[1]
        raw_matches += 1
        if best.distance > cfg.LOWE_RATIO * second.distance:
            continue
        p1 = keypoints[best.queryIdx].pt
        p2 = keypoints[best.trainIdx].pt
        if np.hypot(p1[0] - p2[0], p1[1] - p2[1]) < cfg.MIN_SPATIAL_DISTANCE:
            continue
        if best.queryIdx > best.trainIdx:
            continue
        filtered.append((best, p1, p2))

    if filtered:
        src = np.array([item[1] for item in filtered], dtype=np.float32)
        dst = np.array([item[2] for item in filtered], dtype=np.float32)
    else:
        src = np.zeros((0, 2), dtype=np.float32)
        dst = np.zeros((0, 2), dtype=np.float32)
    inlier_mask, transform_ok = _geometric_inliers(src, dst)
    inlier_src = src[inlier_mask] if len(src) else src
    inlier_dst = dst[inlier_mask] if len(dst) else dst
    geo_count = int(inlier_mask.sum()) if len(inlier_mask) else 0

    clusters = _compact_clusters(inlier_src, inlier_dst, work.shape[1], work.shape[0]) if geo_count else []
    repetition = len(clusters) > cfg.MAX_SMALL_CLUSTERS_BEFORE_PENALTY
    regions = [_to_region(index, cluster, scale) for index, cluster in enumerate(clusters, start=1)]
    score, signals = _score(geo_count, len(filtered), clusters, repetition, work.shape[1] * work.shape[0])
    if repetition:
        limitations.append("Multiple small similar match clusters resemble repeated template elements; suspicion was reduced.")
    confidence = _confidence(clusters, repetition, geo_count)

    evidence: list[ForensicEvidence] = []
    if regions:
        artifact_id = f"p{page_number:03d}_copymove"
        overlay = original.copy()
        for region in regions:
            _draw_pair(overlay, region)
        dest = forensics_dir(settings, analysis_id) / f"{artifact_id}.png"
        cv2.imwrite(str(dest), overlay)
        evidence.append(
            ForensicEvidence(
                type="copy_move_overlay",
                artifact_id=artifact_id,
                description="Source region (cyan) and matched region (amber) with geometrically consistent feature matches.",
            )
        )

    limitations.append("A single feature match is not copy-move evidence. Repeated document structure is filtered.")
    limitations.append("Copy-move signals do not prove that a document was forged.")
    return CopyMovePageResult(
        page_number=page_number,
        suspicion_score=score,
        confidence=confidence,
        flagged=score >= cfg.FLAG_THRESHOLD,
        metrics=CopyMovePageMetrics(
            keypoints_detected=keypoint_count,
            raw_matches=raw_matches,
            filtered_matches=len(filtered),
            geometrically_verified_matches=geo_count,
            suspicious_clusters=len(clusters),
        ),
        regions=regions,
        evidence=evidence,
        signals=signals,
        limitations=limitations,
    )


def _working_image(bgr: np.ndarray) -> tuple[np.ndarray, float, bool]:
    h, w = bgr.shape[:2]
    longest = max(h, w)
    if longest <= cfg.MAX_WORKING_SIDE:
        return bgr, 1.0, False
    scale = cfg.MAX_WORKING_SIDE / longest
    work = cv2.resize(bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return work, scale, True


def _geometric_inliers(src: np.ndarray, dst: np.ndarray) -> tuple[np.ndarray, bool]:
    if len(src) < cfg.MIN_MATCHES_FOR_GEOMETRY:
        return np.zeros(len(src), dtype=bool), False
    matrix, mask = cv2.estimateAffinePartial2D(
        src,
        dst,
        method=cv2.RANSAC,
        ransacReprojThreshold=cfg.RANSAC_REPROJ_THRESHOLD,
        maxIters=2000,
        confidence=0.99,
    )
    if matrix is None or mask is None:
        homography, hmask = cv2.findHomography(src, dst, cv2.RANSAC, cfg.RANSAC_REPROJ_THRESHOLD)
        if homography is None or hmask is None:
            return np.zeros(len(src), dtype=bool), False
        inliers = hmask.ravel().astype(bool)
        return inliers, int(inliers.sum()) >= cfg.MIN_INLIERS
    inliers = mask.ravel().astype(bool)
    if int(inliers.sum()) < cfg.MIN_INLIERS:
        homography, hmask = cv2.findHomography(src, dst, cv2.RANSAC, cfg.RANSAC_REPROJ_THRESHOLD)
        if homography is None or hmask is None:
            return inliers, False
        inliers = hmask.ravel().astype(bool)
        return inliers, int(inliers.sum()) >= cfg.MIN_INLIERS
    return inliers, True


def _compact_clusters(
    src: np.ndarray,
    dst: np.ndarray,
    width: int,
    height: int,
) -> list[dict]:
    if len(src) < cfg.MIN_INLIERS:
        return []
    displacement = dst - src
    # Quantize displacement to group consistent copy-paste translations.
    bin_size = 12.0
    keys = np.round(displacement / bin_size).astype(int)
    groups: dict[tuple[int, int], list[int]] = {}
    for index, key in enumerate(keys):
        groups.setdefault((int(key[0]), int(key[1])), []).append(index)

    clusters: list[dict] = []
    image_area = max(width * height, 1)
    for indices in groups.values():
        if len(indices) < cfg.MIN_INLIERS:
            continue
        s = src[indices]
        d = dst[indices]
        sb = _bbox(s)
        db = _bbox(d)
        if _span_too_large(sb, width, height) or _span_too_large(db, width, height):
            continue
        source_area = max(sb[2] * sb[3], 1)
        dest_area = max(db[2] * db[3], 1)
        if source_area / image_area < cfg.MIN_REGION_AREA_RATIO and dest_area / image_area < cfg.MIN_REGION_AREA_RATIO:
            if len(indices) < cfg.MIN_INLIERS + 4:
                continue
        fill = len(indices) / float(source_area)
        if fill < cfg.MIN_COMPACTNESS_FILL and len(indices) < 16:
            continue
        if _boxes_overlap_heavily(sb, db):
            continue
        clusters.append({"src": sb, "dst": db, "count": len(indices), "fill": fill, "area": max(source_area, dest_area)})
    clusters.sort(key=lambda item: item["count"], reverse=True)
    return clusters[:6]


def _bbox(points: np.ndarray) -> tuple[int, int, int, int]:
    x_min = int(np.floor(points[:, 0].min()))
    y_min = int(np.floor(points[:, 1].min()))
    x_max = int(np.ceil(points[:, 0].max()))
    y_max = int(np.ceil(points[:, 1].max()))
    return x_min, y_min, max(1, x_max - x_min), max(1, y_max - y_min)


def _span_too_large(box: tuple[int, int, int, int], width: int, height: int) -> bool:
    return (box[2] / max(width, 1) > cfg.MAX_REGION_SPAN_RATIO) or (box[3] / max(height, 1) > cfg.MAX_REGION_SPAN_RATIO)


def _boxes_overlap_heavily(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    union = aw * ah + bw * bh - inter
    return union > 0 and inter / union > 0.35


def _to_region(index: int, cluster: dict, scale: float) -> CopyMoveRegion:
    def map_box(box: tuple[int, int, int, int]) -> BoundingBox:
        x, y, w, h = box
        inv = 1.0 / scale
        return BoundingBox(
            x=max(0, int(round(x * inv))),
            y=max(0, int(round(y * inv))),
            width=max(1, int(round(w * inv))),
            height=max(1, int(round(h * inv))),
        )

    strength: str = "low"
    if cluster["count"] >= 28:
        strength = "high"
    elif cluster["count"] >= 14:
        strength = "medium"
    match_confidence = min(1.0, round(0.35 + 0.02 * cluster["count"], 2))
    return CopyMoveRegion(
        region_id=f"cm_{index:02d}",
        source_bbox=map_box(cluster["src"]),
        matched_bbox=map_box(cluster["dst"]),
        match_confidence=match_confidence,
        evidence_strength=strength,
    )


def _score(
    geo_count: int,
    filtered_count: int,
    clusters: list[dict],
    repetition: bool,
    pixel_count: int,
) -> tuple[int, list[MetadataSignal]]:
    signals: list[MetadataSignal] = []
    if not clusters or geo_count < cfg.MIN_INLIERS:
        return 0, signals

    inlier_part = int(round(cfg.SCORE_INLIER_BASE * min(1.0, geo_count / 40.0)))
    ratio = geo_count / max(filtered_count, 1)
    ratio_part = int(round(cfg.SCORE_INLIER_RATIO * min(1.0, max(0.0, ratio - 0.15) / 0.5)))
    top = clusters[0]
    area_part = int(round(cfg.SCORE_REGION_AREA * min(1.0, top["area"] / max(pixel_count * 0.08, 1))))
    compact_part = int(round(cfg.SCORE_COMPACT_CLUSTER * min(1.0, top["count"] / 24.0)))
    consistency = int(round(cfg.SCORE_TRANSFORM_CONSISTENCY * min(1.0, 1.0 if len(clusters) <= 2 else 0.4)))
    score = inlier_part + ratio_part + area_part + compact_part + consistency
    if repetition:
        score = int(round(score * cfg.REPETITION_SCORE_FACTOR))

    signals.append(
        MetadataSignal(
            id="copy_move_verified_cluster",
            finding="Repeated visual pattern detected.",
            severity="high" if score >= cfg.FLAG_THRESHOLD else "medium",
            score_impact=min(100, score),
            detail=(
                f"{geo_count} geometrically consistent matches formed {len(clusters)} compact region pair(s). "
                "This is a potential clone signal, not confirmation of forgery."
            ),
        )
    )
    return min(100, score), signals


def _confidence(clusters: list[dict], repetition: bool, geo_count: int) -> float:
    if not clusters:
        return round(cfg.CONFIDENCE_BASE, 2)
    value = cfg.CONFIDENCE_BASE + cfg.CONFIDENCE_PER_STRONG_CLUSTER * min(2, len(clusters)) + min(0.2, geo_count / 200.0)
    if repetition:
        value = min(value, cfg.CONFIDENCE_REPETITION_CAP)
    return round(min(cfg.CONFIDENCE_MAX, value), 2)


def _draw_pair(image: np.ndarray, region: CopyMoveRegion) -> None:
    s = region.source_bbox
    d = region.matched_bbox
    cv2.rectangle(image, (s.x, s.y), (s.x + s.width, s.y + s.height), (255, 200, 0), 2)
    cv2.rectangle(image, (d.x, d.y), (d.x + d.width, d.y + d.height), (0, 165, 255), 2)
    p1 = (s.x + s.width // 2, s.y + s.height // 2)
    p2 = (d.x + d.width // 2, d.y + d.height // 2)
    cv2.line(image, p1, p2, (80, 80, 80), 1, cv2.LINE_AA)
    cv2.putText(image, "source", (s.x, max(16, s.y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 200, 0), 1, cv2.LINE_AA)
    cv2.putText(image, "match", (d.x, max(16, d.y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 1, cv2.LINE_AA)
