from __future__ import annotations

from pathlib import Path

import cv2
from fastapi import HTTPException, status

from app.core.config import Settings


def signature_dir(settings: Settings, comparison_id: str, *, create: bool = True) -> Path:
    root = settings.processed_path.resolve()
    path = (root / comparison_id / "signature").resolve()
    if not str(path).startswith(str(root)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid storage path.")
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def reference_dir(settings: Settings, *, create: bool = True) -> Path:
    path = (settings.upload_path / "references").resolve()
    if not str(path).startswith(str(settings.upload_path.resolve())):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid storage path.")
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def write_png(path: Path, image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)


def resolve_signature_artifact(settings: Settings, comparison_id: str, artifact_id: str) -> Path:
    allowed = {
        "page-preview",
        "document-signature",
        "document-normalized",
        "document-contours",
        "reference-normalized",
        "overlay",
        "region-highlight",
    }
    if artifact_id not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid artifact identifier.")
    directory = signature_dir(settings, comparison_id, create=False)
    candidate = (directory / f"{artifact_id}.png").resolve()
    try:
        candidate.relative_to(directory)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid artifact identifier.") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")
    return candidate
