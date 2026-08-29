from __future__ import annotations

import cv2

from app.core.logging import get_logger
from app.schemas.intelligence import BarcodeFinding
from app.schemas.preprocessing import PreprocessingResultInternal
from app.schemas.visual import BoundingBox

logger = get_logger(__name__)


def extract_barcodes(preprocessing: PreprocessingResultInternal) -> list[BarcodeFinding]:
    """Decode QR codes with OpenCV. Failure is silent and never raises suspicion."""
    findings: list[BarcodeFinding] = []
    detector = cv2.QRCodeDetector()
    for item in preprocessing.page_images:
        image = cv2.imread(item.path, cv2.IMREAD_COLOR)
        if image is None:
            continue
        try:
            value, points, _ = detector.detectAndDecode(image)
        except Exception:
            logger.info("module=barcode page=%s decode_error", item.page_number)
            continue
        if not value:
            continue
        bbox = None
        if points is not None and len(points) > 0:
            pts = points.reshape(-1, 2)
            x_min, y_min = pts.min(axis=0)
            x_max, y_max = pts.max(axis=0)
            bbox = BoundingBox(
                x=int(x_min),
                y=int(y_min),
                width=max(1, int(x_max - x_min)),
                height=max(1, int(y_max - y_min)),
            )
        findings.append(
            BarcodeFinding(kind="qr", value=value, page_number=item.page_number, bbox=bbox)
        )
    return findings
