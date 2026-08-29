import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import Settings

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
CONTENT_SIGNATURES: dict[str, list[bytes]] = {
    ".pdf": [b"%PDF"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
}


class StoredUpload:
    def __init__(
        self,
        *,
        original_filename: str,
        stored_filename: str,
        file_path: Path,
        file_type: str,
        file_size: int,
        sha256: str,
        content: bytes,
    ) -> None:
        self.original_filename = original_filename
        self.stored_filename = stored_filename
        self.file_path = file_path
        self.file_type = file_type
        self.file_size = file_size
        self.sha256 = sha256
        self.content = content


def sanitize_original_filename(filename: str | None) -> str:
    if not filename:
        return "unnamed"
    name = Path(filename).name
    if not name or name in {".", ".."}:
        return "unnamed"
    return name[:512]


def detect_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_extension(extension: str) -> None:
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Accepted formats: PDF, JPG, JPEG, PNG.",
        )


def validate_content_signature(extension: str, content: bytes) -> None:
    signatures = CONTENT_SIGNATURES[extension]
    if not any(content.startswith(signature) for signature in signatures):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match the declared file type.",
        )


def generate_stored_filename(extension: str) -> str:
    return f"{uuid.uuid4().hex}{extension}"


async def save_upload(upload: UploadFile, settings: Settings, sha256: str) -> StoredUpload:
    original_filename = sanitize_original_filename(upload.filename)
    extension = detect_extension(original_filename)
    validate_extension(extension)

    content = await upload.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the maximum upload size of {settings.max_upload_size_mb} MB.",
        )
    validate_content_signature(extension, content)

    stored_filename = generate_stored_filename(extension)
    destination = settings.upload_path / stored_filename
    if not str(destination.resolve()).startswith(str(settings.upload_path)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid storage path.",
        )
    destination.write_bytes(content)

    return StoredUpload(
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=destination,
        file_type=extension.lstrip("."),
        file_size=len(content),
        sha256=sha256,
        content=content,
    )
