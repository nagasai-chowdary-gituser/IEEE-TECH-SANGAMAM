from __future__ import annotations

import cv2
import numpy as np
from fastapi import HTTPException, status

from app.schemas.signature import SignatureQuality

MIN_WIDTH = 80
MIN_HEIGHT = 32
MIN_INK_RATIO = 0.004
MAX_INK_RATIO = 0.55
CANONICAL_HEIGHT = 128
CANONICAL_WIDTH = 320


def decode_image(content: bytes) -> np.ndarray:
    array = np.frombuffer(content, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The file could not be decoded as an image.")
    return image


def load_bgr(path: str) -> np.ndarray:
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The stored image could not be read.")
    return image


def assess_and_normalize(bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray, SignatureQuality]:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape[:2]
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Signature image is too small. Minimum size is {MIN_WIDTH}×{MIN_HEIGHT} pixels.",
        )
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(blurred)
    binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 8)
    kernel = np.ones((2, 2), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    ink_ratio = float(np.count_nonzero(binary)) / float(binary.size)
    if ink_ratio < MIN_INK_RATIO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No meaningful signature strokes were detected. Blank or nearly blank images cannot be used as a reference.",
        )
    if ink_ratio > MAX_INK_RATIO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The image is too filled to be a signature. Crop to the signature strokes only.",
        )
    cropped_gray, cropped_bin = _crop_to_ink(enhanced, binary)
    normalized = _canonicalize(cropped_bin)
    sharpness = float(cv2.Laplacian(cropped_gray, cv2.CV_64F).var())
    quality = _quality(cropped_gray.shape[1], cropped_gray.shape[0], ink_ratio, sharpness)
    if quality.score < 0.22:
        quality.limitations.append("Reference signature quality is low; comparisons may be inconclusive.")
    return cropped_gray, normalized, quality


def normalize_crop(bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray, SignatureQuality]:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape[:2]
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(blurred)
    binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 8)
    ink_ratio = float(np.count_nonzero(binary)) / float(max(1, binary.size))
    cropped_gray, cropped_bin = _crop_to_ink(enhanced, binary) if ink_ratio >= MIN_INK_RATIO else (enhanced, binary)
    normalized = _canonicalize(cropped_bin)
    sharpness = float(cv2.Laplacian(cropped_gray, cv2.CV_64F).var())
    quality = _quality(width, height, ink_ratio, sharpness)
    if width < 60 or height < 24:
        quality.limitations.append("Extracted signature region has low resolution.")
    if ink_ratio < MIN_INK_RATIO:
        quality.limitations.append("Extracted region contains very little ink.")
        quality.score = min(quality.score, 0.2)
    if sharpness < 18:
        quality.limitations.append("Extracted signature is blurry or heavily compressed.")
    return cropped_gray, normalized, quality


def _crop_to_ink(gray: np.ndarray, binary: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    coords = cv2.findNonZero(binary)
    if coords is None:
        return gray, binary
    x, y, w, h = cv2.boundingRect(coords)
    pad = 8
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(gray.shape[1], x + w + pad)
    y1 = min(gray.shape[0], y + h + pad)
    return gray[y0:y1, x0:x1], binary[y0:y1, x0:x1]


def _canonicalize(binary: np.ndarray) -> np.ndarray:
    height, width = binary.shape[:2]
    if height == 0 or width == 0:
        return np.zeros((CANONICAL_HEIGHT, CANONICAL_WIDTH), dtype=np.uint8)
    scale = CANONICAL_HEIGHT / float(height)
    new_w = max(8, int(round(width * scale)))
    resized = cv2.resize(binary, (new_w, CANONICAL_HEIGHT), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((CANONICAL_HEIGHT, CANONICAL_WIDTH), dtype=np.uint8)
    if new_w >= CANONICAL_WIDTH:
        resized = cv2.resize(binary, (CANONICAL_WIDTH, CANONICAL_HEIGHT), interpolation=cv2.INTER_AREA)
        return resized
    x0 = (CANONICAL_WIDTH - new_w) // 2
    canvas[:, x0 : x0 + new_w] = resized
    return canvas


def _quality(width: int, height: int, ink_ratio: float, sharpness: float) -> SignatureQuality:
    size_score = min(1.0, min(width, height) / 140.0)
    ink_score = 1.0 - min(1.0, abs(ink_ratio - 0.08) / 0.12)
    sharp_score = min(1.0, sharpness / 120.0)
    score = max(0.0, min(1.0, 0.35 * size_score + 0.35 * ink_score + 0.30 * sharp_score))
    limitations: list[str] = []
    if size_score < 0.45:
        limitations.append("Resolution is limited for reliable stroke comparison.")
    if sharp_score < 0.35:
        limitations.append("Stroke edges are soft; structural comparison is less reliable.")
    return SignatureQuality(
        score=round(score, 4),
        width=width,
        height=height,
        ink_ratio=round(ink_ratio, 4),
        sharpness=round(sharpness, 2),
        limitations=limitations,
    )


def encode_png(image: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise RuntimeError("png_encode_failed")
    return encoded.tobytes()
