"""Deterministic metadata-forensics scoring.

These constants are the single source of truth for Phase 1 suspicion scoring.
The same file must always produce the same score. No wall-clock comparisons
are used, because that would make scores change over time.

Philosophy:
- Ordinary or clean metadata stays low.
- Missing metadata is weak evidence (low / low-medium only).
- Known editing software is suspicious context, not proof of forgery.
- Strong timestamp contradictions can reach medium or high depending on evidence.
- Multiple weak signals may accumulate, capped at 100.
"""

FLAG_THRESHOLD = 40

# Missing / stripped metadata — intentionally small impacts.
SCORE_MISSING_CREATOR = 4
SCORE_MISSING_PRODUCER = 3
SCORE_MISSING_CREATION_DATE = 5
SCORE_MISSING_MOD_DATE = 2
SCORE_STRIPPED_METADATA = 8
SCORE_MISSING_EXIF = 6
SCORE_MISSING_IMAGE_SOFTWARE = 3
SCORE_MISSING_IMAGE_DATETIME = 4

# Editing / rewriting software — context, not proof.
SCORE_HIGH_RISK_EDITOR = 28
SCORE_MEDIUM_RISK_EDITOR = 16
SCORE_PDF_REWRITE_TOOL = 14

# Timestamp and consistency signals.
SCORE_MOD_BEFORE_CREATE = 30
SCORE_MEANINGFUL_POST_EDIT = 18
SCORE_XMP_INFO_MISMATCH = 16
SCORE_EXIF_TIMESTAMP_MISMATCH = 22
SCORE_CREATOR_PRODUCER_CONFLICT = 12

# Confidence is derived from how much inspectable metadata was actually present.
CONFIDENCE_BASE = 0.18
CONFIDENCE_PER_FIELD = 0.12
CONFIDENCE_MAX = 0.95

HIGH_RISK_EDITORS = (
    "adobe photoshop",
    "photoshop",
    "gimp",
    "photopea",
    "paint.net",
    "affinity photo",
    "pixelmator",
    "corel paintshop",
    "snagit",
)

MEDIUM_RISK_EDITORS = (
    "canva",
    "pixlr",
    "lightroom",
    "capture one",
)

PDF_REWRITE_TOOLS = (
    "ilovepdf",
    "smallpdf",
    "sejda",
    "pdfescape",
    "pdf24",
    "cute pdf",
    "nitro",
    "soda pdf",
    "wondershare pdfelement",
    "foxit phantom",
)

ORDINARY_PRODUCERS = (
    "adobe acrobat",
    "adobe pdf library",
    "acrobat distiller",
    "microsoft word",
    "microsoft excel",
    "microsoft powerpoint",
    "microsoft: print to pdf",
    "skia/pdf",
    "cairo",
    "quartz pdfcontext",
    "libreoffice",
    "openoffice",
    "prince",
    "itext",
    "reportlab",
    "wkhtmltopdf",
    "chrome",
    "chromium",
    "google",
    "mac os x quartz",
)
