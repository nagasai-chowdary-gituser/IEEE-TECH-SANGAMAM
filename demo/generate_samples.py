"""Generate real sample documents for local testing. Not used as runtime mocks."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tests.fixtures import (  # noqa: E402
    cloned_region_png_bytes,
    conflicting_invoice_pdf_bytes,
    native_pdf_bytes,
    photoshop_pdf_bytes,
    readable_ocr_png_bytes,
)


def main() -> None:
    out = Path(__file__).resolve().parent / "samples"
    out.mkdir(parents=True, exist_ok=True)
    (out / "01-normal.pdf").write_bytes(native_pdf_bytes())
    (out / "02-scanned-like.png").write_bytes(readable_ocr_png_bytes())
    (out / "03-edited-metadata.pdf").write_bytes(photoshop_pdf_bytes())
    (out / "04-copy-move.png").write_bytes(cloned_region_png_bytes())
    (out / "05-arithmetic-inconsistency.pdf").write_bytes(conflicting_invoice_pdf_bytes())
    print(f"Wrote sample files to {out}")


if __name__ == "__main__":
    main()
