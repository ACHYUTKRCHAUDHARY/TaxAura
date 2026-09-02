from pathlib import Path

import pytesseract
from PIL import Image
from pypdf import PdfReader

from aura.core.config import settings


def extract_text(path: Path, mime_type: str) -> str:
    if mime_type == "application/pdf":
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
    with Image.open(path) as image:
        return pytesseract.image_to_string(image).strip()


def split_text(text: str, chunk_size: int = 1_000, overlap: int = 150) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = end - overlap
    return chunks
