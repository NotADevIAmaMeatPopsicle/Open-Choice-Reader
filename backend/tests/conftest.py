from collections.abc import Iterator
from io import BytesIO
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.testclient import TestClient


backend_root = Path(__file__).resolve().parents[1]
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.config import settings  # noqa: E402


AUTH_EXEMPT_MODULES = {
    "test_auth_api",
    "test_multi_user_authorization_api",
    "test_multi_user_backfill",
}


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch) -> Iterator[None]:
    monkeypatch.setattr(settings, "storage_root", tmp_path / "data")
    monkeypatch.setattr(settings, "source_root", tmp_path / "data" / "source")
    monkeypatch.setattr(settings, "cache_root", tmp_path / "data" / "cache")
    monkeypatch.setattr(settings, "export_root", tmp_path / "data" / "exports")
    monkeypatch.setattr(settings, "inbox_root", tmp_path / "data" / "inbox")
    monkeypatch.setattr(settings, "seed_download_root", tmp_path / "data" / "seed-downloads")
    monkeypatch.setattr(settings, "tts_engine", "mock", raising=False)
    monkeypatch.setattr(settings, "piper_binary", "piper", raising=False)
    monkeypatch.setattr(settings, "metadata_enrichment_enabled", False, raising=False)
    monkeypatch.setattr(
        settings,
        "piper_model_path",
        tmp_path / "data" / "models" / "piper" / "test.onnx",
        raising=False,
    )
    yield


@pytest.fixture(autouse=True)
def authenticated_api_client(request: pytest.FixtureRequest) -> Iterator[None]:
    if "client" not in request.fixturenames:
        yield
        return

    module_name = getattr(request.module, "__name__", "")
    module_basename = module_name.rsplit(".", 1)[-1]
    if module_basename in AUTH_EXEMPT_MODULES:
        yield
        return

    client = request.getfixturevalue("client")
    if not isinstance(client, TestClient):
        yield
        return

    me_response = client.get("/api/auth/me")
    if me_response.status_code == 401:
        bootstrap_response = client.post(
            "/api/auth/bootstrap-admin",
            json={
                "username": "admin",
                "display_name": "Admin User",
                "password": "admin-password-123",
            },
        )
        if bootstrap_response.status_code != 201:
            login_response = client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "admin-password-123"},
            )
            assert login_response.status_code == 200, login_response.text

    yield


@pytest.fixture
def epub_fixture_bytes() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=ZIP_DEFLATED)
        archive.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""",
        )
        archive.writestr(
            "OEBPS/content.opf",
            """<?xml version="1.0" encoding="utf-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">fixture-book</dc:identifier>
    <dc:title>Alice Fixture</dc:title>
    <dc:creator>Fixture Author</dc:creator>
    <dc:description>Alice's fixture description.</dc:description>
    <meta name="cover" content="cover-image"/>
  </metadata>
  <manifest>
    <item id="cover-image" href="cover.svg" media-type="image/svg+xml" properties="cover-image"/>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
  </spine>
</package>
""",
        )
        archive.writestr(
            "OEBPS/chapter1.xhtml",
            """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Chapter One</title></head>
  <body>
    <h1>Chapter One</h1>
    <p>Alice reads the first page.</p>
  </body>
</html>
""",
        )
        archive.writestr(
            "OEBPS/cover.svg",
            """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="240" height="360" viewBox="0 0 240 360">
  <rect width="240" height="360" fill="#1f2937"/>
  <text x="24" y="88" fill="#f9fafb" font-family="Georgia" font-size="26">Fixture Cover</text>
  <text x="24" y="136" fill="#cbd5e1" font-family="Georgia" font-size="18">Alice Fixture</text>
</svg>
""",
        )
    return buffer.getvalue()


@pytest.fixture
def epub_relative_fixture_bytes() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=ZIP_DEFLATED)
        archive.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OPS/Package/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""",
        )
        archive.writestr(
            "OPS/Package/content.opf",
            """<?xml version="1.0" encoding="utf-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">relative-fixture-book</dc:identifier>
    <dc:title>Alice Relative Fixture</dc:title>
  </metadata>
  <manifest>
    <item id="chapter1" href="../Text/chapter%201.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
  </spine>
</package>
""",
        )
        archive.writestr(
            "OPS/Text/chapter 1.xhtml",
            """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Escaped Chapter</title></head>
  <body>
    <h1>Escaped Chapter</h1>
    <p>Alice follows a relative EPUB path.</p>
  </body>
</html>
""",
        )
    return buffer.getvalue()


@pytest.fixture
def pdf_fixture_bytes() -> bytes:
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Count 1 /Kids [3 0 R] >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 18 Tf
72 96 Td
(Alice reads quietly.) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000063 00000 n 
0000000122 00000 n 
0000000248 00000 n 
0000000342 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
412
%%EOF
"""
