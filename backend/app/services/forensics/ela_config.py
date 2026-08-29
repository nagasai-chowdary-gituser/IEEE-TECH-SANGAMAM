"""Error Level Analysis configuration and scoring constants.

ELA compares a processing image to a controlled JPEG recompression. Elevated
residuals can indicate mixed compression histories, but they also appear in
ordinary JPEG photographs, screenshots, and PDF rasterizations.

Scoring therefore prefers localized, high-contrast residual clusters over a
high global mean. A globally noisy residual field is treated as weak evidence
and lowers confidence rather than maximizing suspicion.
"""

from __future__ import annotations

JPEG_QUALITY = 90
VISUAL_AMPLIFY = 12.0
MAX_WORKING_SIDE = 2200

# Adaptive high-error mask. Percentile + sigma avoids a single global cutoff
# that would fire on every JPEG.
HIGH_ERROR_PERCENTILE = 93.0
HIGH_ERROR_SIGMA = 1.8
HIGH_ERROR_FLOOR = 8.0

# Ignore speckle. Tiny blobs are typical encoder noise, not cloned content.
MIN_COMPONENT_PIXEL_RATIO = 0.0015
MAX_COMPONENTS_TO_SCORE = 12

# Contrast between a blob and a dilated neighborhood. Low contrast means the
# residual is not distinctive relative to its surroundings.
MIN_LOCAL_CONTRAST = 6.0
STRONG_LOCAL_CONTRAST = 16.0

FLAG_THRESHOLD = 40

# Score contributions (capped later). Intentionally moderate: ELA is not proof.
SCORE_LOCALIZED_CLUSTER = 26
SCORE_CONCENTRATION = 18
SCORE_LOCAL_GLOBAL_GAP = 16
SCORE_EXTREME_PEAK = 10
SCORE_UNIFORM_NOISE_PENALTY = 12

CONFIDENCE_JPEG = 0.62
CONFIDENCE_PNG = 0.30
CONFIDENCE_PDF_RENDER = 0.34
CONFIDENCE_NOISY_DISCOUNT = 0.12
CONFIDENCE_MIN = 0.18
CONFIDENCE_MAX = 0.85
