"""Local signature-region integrity from image statistics around a confirmed crop.

This is not identity verification. Low crop quality yields INCONCLUSIVE.
A single weak local difference is not treated as high manipulation risk.
"""

from __future__ import annotations

import numpy as np

from app.schemas.signature import SignatureQuality, SignatureRegion, StreamAssessment
from app.services.signature.detect import crop_region


def analyze_signature_integrity(page_bgr, region: SignatureRegion | None, quality: SignatureQuality | None) -> StreamAssessment:
    if region is None:
        return StreamAssessment(
            status="INCONCLUSIVE",
            summary="No signature region was confirmed, so signature integrity could not be assessed.",
            limitations=["Signature region was not selected or detected with sufficient confidence."],
        )
    crop = crop_region(page_bgr, region)
    if crop.size == 0:
        return StreamAssessment(
            status="INCONCLUSIVE",
            summary="The signature crop could not be read.",
            limitations=["Signature crop was empty."],
        )
    surround = _surround(page_bgr, region)
    findings: list[str] = []
    limitations: list[str] = []
    quality_score = quality.score if quality else 0.0
    if quality and quality.limitations:
        limitations.extend(quality.limitations)
    if quality_score < 0.34:
        return StreamAssessment(
            status="INCONCLUSIVE",
            summary="Analysis inconclusive due to scan/image quality.",
            confidence=quality_score,
            findings=[],
            limitations=limitations + ["Signature crop quality was too low for a reliable local integrity assessment."],
        )

    crop_noise = _highpass_std(crop)
    surround_noise = _highpass_std(surround) if surround is not None else None
    edge_gap = _border_interior_gap(crop)
    corroboration = 0
    if surround_noise is not None and surround_noise > 1e-6:
        noise_ratio = abs(crop_noise - surround_noise) / max(surround_noise, 1e-6)
        if noise_ratio >= 0.85:
            corroboration += 1
            findings.append(
                "Local noise characteristics in the signature crop differed from the immediately surrounding certificate area."
            )
        elif noise_ratio >= 0.45:
            findings.append(
                "Mild noise inconsistency was measured between the signature crop and surrounding paper. This alone is not treated as high-risk evidence."
            )
    if edge_gap >= 18.0:
        corroboration += 1
        findings.append("Edge energy along the crop boundary was inconsistent with the interior of the signature region.")
    elif edge_gap >= 9.0:
        findings.append("A moderate boundary/interior edge difference was measured around the signature crop.")

    if corroboration >= 2 and quality_score >= 0.5:
        status = "ELEVATED_MANIPULATION_RISK"
        summary = "Multiple forensic inconsistencies detected around the signature region."
    elif corroboration >= 1 and findings:
        status = "REVIEW_REQUIRED"
        summary = "Suspicious region detected requiring review."
    elif quality_score < 0.5:
        status = "LOW_MANIPULATION_RISK"
        summary = "No significant manipulation evidence detected in the completed analysis."
        limitations.append("Signature image quality reduced confidence in local integrity measurements.")
    else:
        status = "NO_SIGNIFICANT_MANIPULATION_EVIDENCE"
        summary = "No significant manipulation evidence detected in the completed analysis."

    return StreamAssessment(
        status=status,
        summary=summary,
        confidence=round(min(1.0, 0.35 + 0.65 * quality_score), 4),
        findings=findings[:6],
        limitations=limitations[:6],
    )


def awaiting_selection(candidates: int) -> StreamAssessment:
    return StreamAssessment(
        status="AWAITING_SELECTION",
        summary="Automatic signature detection was uncertain. Confirm the correct signature region before signature integrity is scored.",
        findings=[f"{candidates} signature-like candidate(s) were detected."] if candidates else [],
        limitations=["Signature integrity is withheld until a region is confirmed so the wrong crop is not scored silently."],
    )


def _surround(page_bgr, region: SignatureRegion, pad: int = 14):
    h, w = page_bgr.shape[:2]
    x0 = max(0, region.x - pad)
    y0 = max(0, region.y - pad)
    x1 = min(w, region.x + region.width + pad)
    y1 = min(h, region.y + region.height + pad)
    ring = page_bgr[y0:y1, x0:x1].copy()
    if ring.size == 0:
        return None
    ix0 = region.x - x0
    iy0 = region.y - y0
    ix1 = ix0 + region.width
    iy1 = iy0 + region.height
    ring[max(0, iy0) : max(0, iy1), max(0, ix0) : max(0, ix1)] = 0
    if np.count_nonzero(cv2_gray(ring) > 0) < 80:
        return None
    return ring


def cv2_gray(image):
    import cv2

    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _highpass_std(image) -> float:
    import cv2

    gray = cv2_gray(image).astype(np.float32)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    return float(np.std(gray - blur))


def _border_interior_gap(image) -> float:
    import cv2

    gray = cv2_gray(image).astype(np.float32)
    if min(gray.shape[:2]) < 12:
        return 0.0
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    border = np.concatenate([mag[:3, :].ravel(), mag[-3:, :].ravel(), mag[:, :3].ravel(), mag[:, -3:].ravel()])
    interior = mag[3:-3, 3:-3]
    if interior.size == 0:
        return 0.0
    return abs(float(np.mean(border)) - float(np.mean(interior)))
