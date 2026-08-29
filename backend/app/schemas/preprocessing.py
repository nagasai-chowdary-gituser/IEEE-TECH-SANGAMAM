from pydantic import BaseModel, Field

from app.schemas.common import DocumentType


class PageImagePublic(BaseModel):
    page_number: int
    width: int
    height: int


class PageImageInternal(PageImagePublic):
    path: str


class PreprocessingResultInternal(BaseModel):
    document_type: DocumentType
    page_count: int
    page_images: list[PageImageInternal]
    processing_notes: list[str] = Field(default_factory=list)
    pdf_info: dict | None = None
    image_format: str | None = None


class PreprocessingResultPublic(BaseModel):
    document_type: DocumentType
    page_count: int
    pages: list[PageImagePublic]
    processing_notes: list[str] = Field(default_factory=list)
    pdf_info: dict | None = None
    image_format: str | None = None

    @classmethod
    def from_internal(cls, result: PreprocessingResultInternal) -> "PreprocessingResultPublic":
        return cls(
            document_type=result.document_type,
            page_count=result.page_count,
            pages=[
                PageImagePublic(page_number=p.page_number, width=p.width, height=p.height)
                for p in result.page_images
            ],
            processing_notes=result.processing_notes,
            pdf_info=result.pdf_info,
            image_format=result.image_format,
        )
