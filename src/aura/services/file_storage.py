import hashlib
from pathlib import Path
from uuid import UUID

import aiofiles
from fastapi import UploadFile

from aura.core.config import settings

CHUNK_SIZE = 1024 * 1024
FILE_SIGNATURES = {
    "application/pdf": (b"%PDF-", ".pdf"),
    "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
    "image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
}


class InvalidFileSignatureError(ValueError):
    pass


class UploadTooLargeError(ValueError):
    pass


async def save_upload(document_id: UUID, file: UploadFile) -> tuple[Path, str]:
    if file.content_type not in FILE_SIGNATURES:
        raise InvalidFileSignatureError("Unsupported media type.")
    signature, suffix = FILE_SIGNATURES[file.content_type]
    await file.seek(0)
    header = await file.read(max(len(signature), 8))
    if not header.startswith(signature):
        raise InvalidFileSignatureError("File contents do not match the declared media type.")
    await file.seek(0)

    destination = settings.upload_directory / f"{document_id}{suffix}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    checksum = hashlib.sha256()
    size = 0
    try:
        async with aiofiles.open(destination, "wb") as output:
            while chunk := await file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > settings.max_upload_size_mb * 1024 * 1024:
                    raise UploadTooLargeError(
                        f"File must be at most {settings.max_upload_size_mb} MB."
                    )
                checksum.update(chunk)
                await output.write(chunk)
        destination.chmod(0o600)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination, checksum.hexdigest()
