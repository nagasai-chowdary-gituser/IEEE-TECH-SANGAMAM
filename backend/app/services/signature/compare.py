from __future__ import annotations

import cv2
import numpy as np

from app.schemas.signature import ComparisonSignals, SignatureQuality


def compare_normalized(
    document_bin: np.ndarray,
    reference_bin: np.ndarray,
    document_quality: SignatureQuality,
    reference_quality: SignatureQuality,
    detection_confidence: float | None,
) -> ComparisonSignals:
    unavailable: list[str] = []
    structural = _ssim(document_bin, reference_bin)
    contour = _contour_similarity(document_bin, reference_bin)
    geometry = _geometry_similarity(document_bin, reference_bin)
    histogram = _histogram_similarity(document_bin, reference_bin)
    feature = _orb_similarity(document_bin, reference_bin)
    if feature is None:
        unavailable.append("feature_match_score")
    quality = min(document_quality.score, reference_quality.score)
    return ComparisonSignals(
        structural_similarity=_clip(structural),
        contour_similarity=_clip(contour),
        feature_match_score=_clip(feature) if feature is not None else None,
        geometry_similarity=_clip(geometry),
        histogram_similarity=_clip(histogram),
        image_quality_score=_clip(quality),
        region_detection_confidence=_clip(detection_confidence) if detection_confidence is not None else None,
        unavailable=unavailable,
    )


def render_overlay(document_bin: np.ndarray, reference_bin: np.ndarray) -> np.ndarray:
    doc = cv2.cvtColor(document_bin, cv2.COLOR_GRAY2BGR)
    ref = cv2.cvtColor(reference_bin, cv2.COLOR_GRAY2BGR)
    overlay = np.zeros_like(doc)
    overlay[:, :, 2] = document_bin
    overlay[:, :, 1] = reference_bin
    return np.hstack([doc, overlay, ref])


def render_contours(binary: np.ndarray) -> np.ndarray:
    color = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(color, contours, -1, (36, 92, 210), 1)
    return color


def _ssim(a: np.ndarray, b: np.ndarray) -> float:
    a64 = a.astype(np.float64)
    b64 = b.astype(np.float64)
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    mu1 = cv2.GaussianBlur(a64, (11, 11), 1.5)
    mu2 = cv2.GaussianBlur(b64, (11, 11), 1.5)
    mu1_sq = mu1 * mu1
    mu2_sq = mu2 * mu2
    mu12 = mu1 * mu2
    sigma1_sq = cv2.GaussianBlur(a64 * a64, (11, 11), 1.5) - mu1_sq
    sigma2_sq = cv2.GaussianBlur(b64 * b64, (11, 11), 1.5) - mu2_sq
    sigma12 = cv2.GaussianBlur(a64 * b64, (11, 11), 1.5) - mu12
    ssim_map = ((2 * mu12 + c1) * (2 * sigma12 + c2)) / ((mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2))
    return float(np.mean(ssim_map))


def _contour_similarity(a: np.ndarray, b: np.ndarray) -> float:
    ca = _largest_contour(a)
    cb = _largest_contour(b)
    if ca is None or cb is None:
        return 0.0
    distance = cv2.matchShapes(ca, cb, cv2.CONTOURS_MATCH_I1, 0.0)
    return float(max(0.0, 1.0 / (1.0 + distance * 8.0)))


def _largest_contour(binary: np.ndarray):
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    return max(contours, key=cv2.contourArea)


def _geometry_similarity(a: np.ndarray, b: np.ndarray) -> float:
    ra = _ink_rect(a)
    rb = _ink_rect(b)
    if ra is None or rb is None:
        return 0.0
    aspect_a = ra[2] / float(max(1, ra[3]))
    aspect_b = rb[2] / float(max(1, rb[3]))
    aspect = 1.0 - min(1.0, abs(aspect_a - aspect_b) / 3.0)
    fill_a = float(np.count_nonzero(a)) / float(max(1, ra[2] * ra[3]))
    fill_b = float(np.count_nonzero(b)) / float(max(1, rb[2] * rb[3]))
    fill = 1.0 - min(1.0, abs(fill_a - fill_b) / 0.25)
    return float((aspect + fill) / 2.0)


def _ink_rect(binary: np.ndarray) -> tuple[int, int, int, int] | None:
    coords = cv2.findNonZero(binary)
    if coords is None:
        return None
    return cv2.boundingRect(coords)


def _histogram_similarity(a: np.ndarray, b: np.ndarray) -> float:
    ha = cv2.calcHist([a], [0], None, [32], [0, 256])
    hb = cv2.calcHist([b], [0], None, [32], [0, 256])
    cv2.normalize(ha, ha)
    cv2.normalize(hb, hb)
    corr = cv2.compareHist(ha, hb, cv2.HISTCMP_CORREL)
    return float((corr + 1.0) / 2.0)


def _orb_similarity(a: np.ndarray, b: np.ndarray) -> float | None:
    orb = cv2.ORB_create(nfeatures=400)
    kp1, des1 = orb.detectAndCompute(a, None)
    kp2, des2 = orb.detectAndCompute(b, None)
    if des1 is None or des2 is None or len(kp1) < 8 or len(kp2) < 8:
        return None
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = matcher.match(des1, des2)
    if not matches:
        return None
    good = [item for item in matches if item.distance < 64]
    denom = float(min(len(kp1), len(kp2)))
    return float(min(1.0, len(good) / max(1.0, denom * 0.35)))


def _clip(value: float | None) -> float | None:
    if value is None:
        return None
    return round(max(0.0, min(1.0, float(value))), 4)
