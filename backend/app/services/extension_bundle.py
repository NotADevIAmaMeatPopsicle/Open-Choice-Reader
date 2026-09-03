from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


EXTENSION_FILES = (
    "manifest.json",
    "popup.html",
    "popup.css",
    "popup.js",
    "background.js",
    "core.js",
    "README.md",
)


def build_chromium_extension_zip() -> bytes:
    extension_root = Path(__file__).resolve().parents[3] / "browser-extension"
    buffer = BytesIO()

    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for relative_name in EXTENSION_FILES:
            file_path = extension_root / relative_name
            archive.writestr(relative_name, file_path.read_bytes())

    return buffer.getvalue()
