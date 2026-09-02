from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from aura.services.file_storage import InvalidFileSignatureError, save_upload


@pytest.mark.asyncio
async def test_rejects_spoofed_pdf() -> None:
    upload = UploadFile(
        file=BytesIO(b"this is not a real pdf"),
        filename="fake.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )
    with pytest.raises(InvalidFileSignatureError):
        await save_upload(uuid4(), upload)
