from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import Settings

ARTIFACT_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,120}$")
FORENSICS_DIRNAME = "forensics"


def _safe_analysis_id(analysis_id: str) -> str:
    try:
        return str(uuid.UUID(analysis_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid analysis ID.") from exc


def forensics_dir(settings: Settings, analysis_id: str, *, create: bool = True) -> Path:
    safe_id = _safe_analysis_id(analysis_id)
    root = settings.processed_path.resolve()
    path = (root / safe_id / FORENSICS_DIRNAME).resolve()
    if not str(path).startswith(str(root)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid artifact directory.")
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_artifact_path(settings: Settings, analysis_id: str, artifact_id: str) -> Path:
    if not ARTIFACT_ID_RE.match(artifact_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid artifact identifier.")
    directory = forensics_dir(settings, analysis_id, create=False)
    candidate = (directory / f"{artifact_id}.png").resolve()
    try:
        candidate.relative_to(directory)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid artifact identifier.") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")
    return candidate
