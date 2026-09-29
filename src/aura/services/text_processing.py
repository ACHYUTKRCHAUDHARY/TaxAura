from pathlib import Path

import pytesseract
from PIL import Image
from pypdf import PdfReader

from aura.core.config import settings


def extract_text(path: Path, mime_type: str) -> str:
    if mime_type == "application/pdf":
        reader = PdfReader(path)
        if len(reader.pages) > 100:
            raise ValueError("Document exceeds 100 pages")
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        if len(text) > 200_000:
            raise ValueError("Document text exceeds processing limit")
        return text
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
    with Image.open(path) as image:
        return pytesseract.image_to_string(image, timeout=30).strip()


def split_text(text: str, chunk_size: int = 1_000, overlap: int = 150) -> list[str]:
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Require chunk_size > overlap >= 0")
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
