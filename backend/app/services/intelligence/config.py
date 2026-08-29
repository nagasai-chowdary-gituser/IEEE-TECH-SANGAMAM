"""Document-intelligence scoring and extraction thresholds.

Insufficient data never adds suspicion. Low OCR quality reduces confidence
only. Confirmed logical contradictions can accumulate; weak matches stay low.
"""

from __future__ import annotations
from decimal import Decimal

# Field extraction
MIN_FIELD_CONFIDENCE = 0.58
MONEY_TOLERANCE = Decimal("0.05")

# OCR quality (Tesseract conf is 0–100)
OCR_HIGH_MEAN = 75.0
OCR_MEDIUM_MEAN = 50.0
OCR_LOW_MEAN = 20.0
OCR_MIN_TOKENS_HIGH = 12
LOW_TOKEN_CONFIDENCE = 40.0

# Native PDF text quality
NATIVE_HIGH_WORDS = 40
NATIVE_MEDIUM_WORDS = 12

# Logical scoring
FLAG_THRESHOLD = 40
SCORE_ARITHMETIC_FAIL = 28
SCORE_DOB_AGE_FAIL = 22
SCORE_DATE_ORDER_FAIL = 18
SCORE_DUPLICATE_FAIL = 16
SCORE_IDENTIFIER_FAIL = 10
SCORE_QR_CONFLICT = 24
WARNING_FACTOR = 0.45

CONFIDENCE_QUALITY = {"high": 0.86, "medium": 0.58, "low": 0.32, "failed": 0.12}
CONFIDENCE_MAX = 0.92
CONFIDENCE_MIN = 0.10
