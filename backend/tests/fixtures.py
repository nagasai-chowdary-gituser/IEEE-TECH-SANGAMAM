from __future__ import annotations

from io import BytesIO
from pathlib import Path

import cv2
import fitz
import numpy as np
from PIL import Image


def native_pdf_bytes(text: str | None = None) -> bytes:
    body = text or (
        "This is a native PDF generated for DocuVerify tests. "
        "It contains a substantial amount of selectable text so classification "
        "does not treat a handful of characters as a native document. "
        "Additional sentences increase token count above the native threshold. "
        "Document forensics preprocessing should classify this file as native_pdf."
    )
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), body, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


def scanned_like_pdf_bytes() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "x", fontsize=8)
    data = doc.tobytes()
    doc.close()
    return data


def photoshop_pdf_bytes() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Export from an editor. " * 20, fontsize=11)
    doc.set_metadata(
        {
            "creator": "Adobe Photoshop 24.7",
            "producer": "Adobe Photoshop PDF",
            "creationDate": "D:20240101120000",
            "modDate": "D:20240101120000",
        }
    )
    data = doc.tobytes()
    doc.close()
    return data


def empty_metadata_pdf_bytes() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Plain generated PDF with default or empty metadata. " * 8)
    doc.set_metadata(
        {
            "creator": "",
            "producer": "",
            "creationDate": "",
            "modDate": "",
            "title": "",
            "author": "",
        }
    )
    data = doc.tobytes()
    doc.close()
    return data


def png_bytes(color: tuple[int, int, int] = (240, 240, 240)) -> bytes:
    image = Image.new("RGB", (128, 96), color=color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def jpeg_with_software(software: str) -> bytes:
    image = Image.new("RGB", (96, 96), color=(250, 250, 250))
    exif = image.getexif()
    exif[305] = software
    buffer = BytesIO()
    image.save(buffer, format="JPEG", exif=exif, quality=90)
    return buffer.getvalue()


def jpeg_without_exif() -> bytes:
    image = Image.new("RGB", (96, 96), color=(245, 245, 245))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def write_temp(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def smooth_jpeg_bytes() -> bytes:
    width, height = 240, 180
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            pixels[x, y] = (200, 198, 196)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()


def textured_array(seed: int, width: int = 420, height: int = 320) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noise = rng.integers(40, 220, size=(height, width, 3), dtype=np.uint8)
    return cv2.GaussianBlur(noise, (5, 5), 0)


def cloned_region_png_bytes() -> bytes:
    image = textured_array(7)
    patch = image[40:140, 50:170].copy()
    image[160:260, 230:350] = patch
    success, encoded = cv2.imencode(".png", image)
    assert success
    return encoded.tobytes()


def repeated_icon_png_bytes() -> bytes:
    canvas = np.full((320, 320, 3), 245, dtype=np.uint8)
    icon = np.zeros((18, 18, 3), dtype=np.uint8)
    icon[:] = (30, 30, 30)
    cv2.rectangle(icon, (3, 3), (14, 14), (200, 200, 200), -1)
    for row in range(10):
        for col in range(10):
            y = 20 + row * 28
            x = 20 + col * 28
            canvas[y : y + 18, x : x + 18] = icon
    success, encoded = cv2.imencode(".png", canvas)
    assert success
    return encoded.tobytes()


def _pdf_from_lines(lines: list[str], fontsize: int = 12) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line, fontsize=fontsize)
        y += fontsize + 6
    data = doc.tobytes()
    doc.close()
    return data


def invoice_pdf_bytes(*, total: str = "118.00") -> bytes:
    return _pdf_from_lines(
        [
            "INVOICE",
            "Invoice Number: INV-1001",
            "Issue Date: 2024-01-10",
            "Due Date: 2024-02-10",
            "Quantity: 2",
            "Unit Price: 50.00",
            "Line Total: 100.00",
            "Subtotal: 100.00",
            "Tax: 18.00",
            f"Total: {total}",
        ]
    )


def certificate_pdf_bytes(*, age: str = "34") -> bytes:
    return _pdf_from_lines(
        [
            "CERTIFICATE",
            "Name: Jane Doe",
            "Date of Birth: 1990-06-15",
            f"Age: {age}",
            "Issue Date: 2024-06-20",
            "Document Number: CERT-7788",
        ]
    )


def conflicting_invoice_pdf_bytes() -> bytes:
    return _pdf_from_lines(
        [
            "INVOICE",
            "Invoice Number: INV-1001",
            "Invoice Number: INV-9999",
            "Issue Date: 2024-01-10",
            "Quantity: 2",
            "Unit Price: 50.00",
            "Line Total: 80.00",
            "Subtotal: 100.00",
            "Tax: 18.00",
            "Total: 12500.00",
        ]
    )


def udyam_certificate_pdf_bytes(
    *,
    pan: str = "AAPFU0939F",
    gstin: str = "27AAPFU0939F1ZV",
    include_pan: bool = True,
    include_gstin: bool = True,
) -> bytes:
    lines = [
        "UDYAM REGISTRATION CERTIFICATE",
        "Name of Enterprise: Sample Precision Works",
        "UDYAM-MH-12-0001234",
        "Date of Registration: 12/01/2022",
    ]
    if include_pan:
        lines.append(f"PAN: {pan}")
    if include_gstin:
        lines.append(f"GSTIN: {gstin}")
    lines.append("This certificate is issued for MSME registration purposes.")
    return _pdf_from_lines(lines)


def readable_ocr_png_bytes() -> bytes:
    image = Image.new("RGB", (640, 120), color=(255, 255, 255))
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    draw.text((20, 40), "Invoice Number INV-4242 Total 10.00", fill=(0, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def blank_png_bytes() -> bytes:
    image = Image.new("RGB", (320, 120), color=(255, 255, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def signature_stroke_png_bytes(*, seed: int = 3, shift: int = 0, scale: float = 1.0) -> bytes:
    width, height = int(360 * scale), int(140 * scale)
    canvas = np.full((height, width, 3), 255, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    points = []
    x = int(24 * scale)
    y = int((70 + shift) * scale)
    for _ in range(48):
        x += int(6 * scale)
        y += int(rng.integers(-7, 8) * scale)
        y = int(np.clip(y, 18 * scale, height - 18 * scale))
        points.append((x, y))
    cv2.polylines(canvas, [np.array(points, dtype=np.int32)], False, (20, 20, 20), max(2, int(3 * scale)))
    cv2.ellipse(
        canvas,
        (int(80 * scale), int(90 * scale)),
        (int(28 * scale), int(10 * scale)),
        18,
        0,
        180,
        (20, 20, 20),
        max(2, int(2 * scale)),
    )
    success, encoded = cv2.imencode(".png", canvas)
    assert success
    return encoded.tobytes()


def certificate_with_signature_png_bytes(*, seed: int = 3) -> bytes:
    canvas = np.full((640, 480, 3), 255, dtype=np.uint8)
    cv2.putText(canvas, "COLLEGE CERTIFICATE", (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 2)
    cv2.putText(canvas, "This is to certify completion.", (40, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1)
    sig = cv2.imdecode(np.frombuffer(signature_stroke_png_bytes(seed=seed), dtype=np.uint8), cv2.IMREAD_COLOR)
    y0, x0 = 470, 80
    h, w = sig.shape[:2]
    canvas[y0 : y0 + h, x0 : x0 + w] = sig
    success, encoded = cv2.imencode(".png", canvas)
    assert success
    return encoded.tobytes()
