"""Deterministic fusion constants.

Scores are not averaged. The strongest reliable layer dominates; independent
layers above the evidence threshold add a capped corroboration bonus.
Failed or unavailable layers reduce coverage and confidence; they are not
treated as clean (zero-risk) results.
"""

from __future__ import annotations

MEANINGFUL_RAW_SCORE = 32
MEANINGFUL_EFFECTIVE = 22
MEANINGFUL_RELIABILITY = 0.38
STRONG_EFFECTIVE = 55
STRONG_RELIABILITY = 0.70

# Fusion mix: max dominates; second layer and remainder cannot hide a spike.
WEIGHT_MAX = 0.70
WEIGHT_SECOND = 0.20
WEIGHT_REST = 0.10

# Corroboration bonus by count of independent layers with meaningful evidence.
# One layer is isolated (no bonus). Cap prevents runaway inflation.
CORROBORATION_BONUS = {0: 0, 1: 0, 2: 10, 3: 16, 4: 20}
CORROBORATION_CAP = 20

COVERAGE_AVAILABLE = 1.0
COVERAGE_LIMITED = 0.45
COVERAGE_FAILED = 0.0
COVERAGE_UNAVAILABLE = 0.0

INCONCLUSIVE_COVERAGE = 0.34
INCONCLUSIVE_MIN_USABLE_LAYERS = 2

HIGH_SCORE = 70
ELEVATED_SCORE = 48
MODERATE_SCORE = 28
