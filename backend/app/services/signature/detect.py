from __future__ import annotations

import cv2
import numpy as np

from app.schemas.signature import SignatureRegion


def detect_signature_regions(page_bgr: np.ndarray, page_number: int = 1) -> list[SignatureRegion]:
    gray = cv2.cvtColor(page_bgr, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape[:2]
    enhanced = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 10)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
    merged = cv2.dilate(binary, kernel, iterations=1)
    contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    page_area = float(width * height)
    candidates: list[SignatureRegion] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < page_area * 0.002 or area > page_area * 0.18:
            continue
        if h < 18 or w < 40:
            continue
        aspect = w / float(h)
        if aspect < 1.15 or aspect > 9.5:
            continue
        roi = binary[y : y + h, x : x + w]
        ink = float(np.count_nonzero(roi)) / float(max(1, roi.size))
        if ink < 0.015 or ink > 0.45:
            continue
        bottom = y / float(height)
        position = 0.55 + 0.45 * bottom if bottom >= 0.42 else 0.25 + 0.3 * bottom
        aspect_score = 1.0 - min(1.0, abs(aspect - 3.2) / 4.0)
        ink_score = 1.0 - min(1.0, abs(ink - 0.08) / 0.12)
        score = max(0.0, min(1.0, 0.40 * position + 0.30 * aspect_score + 0.30 * ink_score))
        candidates.append(
            SignatureRegion(
                page_number=page_number,
                x=int(x),
                y=int(y),
                width=int(w),
                height=int(h),
                score=round(score, 4),
                source="auto",
                reason="Connected ink region with signature-like geometry.",
            )
        )
    candidates.sort(key=lambda item: item.score or 0, reverse=True)
    return candidates[:8]


def crop_region(page_bgr: np.ndarray, region: SignatureRegion) -> np.ndarray:
    h, w = page_bgr.shape[:2]
    x0 = max(0, min(w - 1, region.x))
    y0 = max(0, min(h - 1, region.y))
    x1 = max(x0 + 1, min(w, region.x + region.width))
    y1 = max(y0 + 1, min(h, region.y + region.height))
    return page_bgr[y0:y1, x0:x1].copy()
