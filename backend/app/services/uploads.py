from fastapi import UploadFile


CHUNK_SIZE = 1024 * 1024


def read_upload_bytes(upload: UploadFile, *, max_bytes: int) -> bytes:
    body = bytearray()
    while chunk := upload.file.read(CHUNK_SIZE):
        body.extend(chunk)
        if len(body) > max_bytes:
            raise ValueError(f"The uploaded file exceeds the {max_bytes}-byte limit")
    return bytes(body)


async def read_upload_bytes_async(upload: UploadFile, *, max_bytes: int) -> bytes:
    body = bytearray()
    while chunk := await upload.read(CHUNK_SIZE):
        body.extend(chunk)
        if len(body) > max_bytes:
            raise ValueError(f"The uploaded file exceeds the {max_bytes}-byte limit")
    return bytes(body)
