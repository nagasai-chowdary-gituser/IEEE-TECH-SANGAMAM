from typing import Literal

from pydantic import BaseModel, Field


Severity = Literal["low", "medium", "high"]
DocumentType = Literal["native_pdf", "scanned_pdf", "image"]
FileType = Literal["pdf", "jpg", "jpeg", "png"]


class ErrorResponse(BaseModel):
    detail: str
