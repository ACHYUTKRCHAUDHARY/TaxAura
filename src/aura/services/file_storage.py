import hashlib
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from aura.core.config import settings


async def save_upload(document_id: UUID, file: UploadFile) -> tuple[Path, str]:
    content = await file.read()
    checksum = hashlib.sha256(content).hexdigest()
    suffix = Path(file.filename or "document").suffix.lower()
    destination = settings.upload_directory / f"{document_id}{suffix}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return destination, checksum
