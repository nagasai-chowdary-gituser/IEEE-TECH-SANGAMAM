from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.schemas.preprocessing import PageImageInternal, PreprocessingResultInternal


def process_image(file_path: Path, output_dir: Path) -> PreprocessingResultInternal:
    output_dir.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []

    with Image.open(file_path) as image:
        image.verify()

    with Image.open(file_path) as image:
        original_format = (image.format or file_path.suffix.lstrip(".")).upper()
        oriented = ImageOps.exif_transpose(image) or image
        if oriented.getexif() and oriented is not image:
            notes.append("Applied EXIF orientation without altering the original file.")
        rgb = oriented.convert("RGB")
        width, height = rgb.size
        array = np.array(rgb)
        bgr = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
        destination = output_dir / "page_001.png"
        if not cv2.imwrite(str(destination), bgr):
            raise RuntimeError("Failed to write processing image copy.")
        notes.append("Created an RGB processing copy. The original upload was left unchanged.")

    return PreprocessingResultInternal(
        document_type="image",
        page_count=1,
        page_images=[
            PageImageInternal(
                page_number=1,
                path=str(destination),
                width=width,
                height=height,
            )
        ],
        processing_notes=notes,
        image_format=original_format,
    )
