from fastapi import APIRouter, Response

from app.services.extension_bundle import build_chromium_extension_zip


router = APIRouter(prefix="/api/extension", tags=["extension"])


@router.get("/chromium")
def download_chromium_extension_bundle() -> Response:
    payload = build_chromium_extension_zip()
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="open-choice-reader-chromium-extension.zip"'},
    )
