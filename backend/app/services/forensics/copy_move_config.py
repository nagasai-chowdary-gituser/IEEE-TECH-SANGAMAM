"""Copy-move detection thresholds.

Documents contain repeated letters, rules, logos, and table cells. A single
ORB match, or a cloud of inconsistent matches, is not cloned-region evidence.

The pipeline requires a spatially distant, geometrically consistent cluster
whose keypoints are compact in both the source and destination regions.
"""

from __future__ import annotations

# Feature extraction is resized for speed; bboxes are mapped back to the
# processing image. The high-resolution file is not overwritten.
MAX_WORKING_SIDE = 1400
ORB_FEATURES = 4000

# Lowe ratio: reject ambiguous descriptor matches.
LOWE_RATIO = 0.72

# Nearby keypoints are the same structure, not a clone.
MIN_SPATIAL_DISTANCE = 48.0

# A handful of matches is noise. Homography/affine needs a real cluster.
MIN_MATCHES_FOR_GEOMETRY = 8
MIN_INLIERS = 10
RANSAC_REPROJ_THRESHOLD = 3.0

# Compact cloned blocks occupy a bounded region, not the whole text column.
MAX_REGION_SPAN_RATIO = 0.48
MIN_REGION_AREA_RATIO = 0.004
MIN_COMPACTNESS_FILL = 8e-6

# Many tiny similar clusters look like template repetition, not one paste.
MAX_SMALL_CLUSTERS_BEFORE_PENALTY = 4
REPETITION_SCORE_FACTOR = 0.55

FLAG_THRESHOLD = 42

SCORE_INLIER_BASE = 22
SCORE_INLIER_RATIO = 18
SCORE_REGION_AREA = 16
SCORE_TRANSFORM_CONSISTENCY = 14
SCORE_COMPACT_CLUSTER = 12

CONFIDENCE_BASE = 0.28
CONFIDENCE_PER_STRONG_CLUSTER = 0.18
CONFIDENCE_MAX = 0.82
CONFIDENCE_REPETITION_CAP = 0.40
