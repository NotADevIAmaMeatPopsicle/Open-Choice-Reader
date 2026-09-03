from io import BytesIO

import pytest
from starlette.datastructures import UploadFile

from app.services.uploads import read_upload_bytes


def test_read_upload_bytes_accepts_content_at_limit() -> None:
    upload = UploadFile(file=BytesIO(b"1234"), filename="sample.txt")
    assert read_upload_bytes(upload, max_bytes=4) == b"1234"


def test_read_upload_bytes_rejects_content_over_limit() -> None:
    upload = UploadFile(file=BytesIO(b"12345"), filename="sample.txt")
    with pytest.raises(ValueError, match="uploaded file exceeds"):
        read_upload_bytes(upload, max_bytes=4)
