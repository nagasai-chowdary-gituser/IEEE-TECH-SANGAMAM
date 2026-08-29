from pathlib import Path

from app.core.config import Settings
from app.schemas.preprocessing import PreprocessingResultInternal
from app.services.preprocessing.image import process_image
from app.services.preprocessing.pdf import process_pdf


def process_document(
    file_path: str,
    *,
    analysis_id: str,
    file_type: str,
    settings: Settings,
) -> PreprocessingResultInternal:
    source = Path(file_path)
    output_dir = settings.processed_path / analysis_id
    if file_type == "pdf":
        return process_pdf(source, output_dir)
    return process_image(source, output_dir)
