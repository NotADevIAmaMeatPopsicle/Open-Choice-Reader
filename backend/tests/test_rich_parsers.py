from importlib import import_module, reload
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from starlette.datastructures import Headers, UploadFile


def test_parse_epub_bytes_returns_titled_sections(epub_fixture_bytes: bytes) -> None:
    parser_module = import_module("app.parsers.epub")
    parser_module = reload(parser_module)

    sections = parser_module.parse_epub_bytes(epub_fixture_bytes)

    assert sections
    assert sections[0].title
    assert "Alice" in sections[0].text


def test_parse_epub_document_returns_metadata_and_cover(epub_fixture_bytes: bytes) -> None:
    parser_module = import_module("app.parsers.epub")
    parser_module = reload(parser_module)

    parsed_document = parser_module.parse_epub_document(epub_fixture_bytes)

    assert parsed_document.title == "Alice Fixture"
    assert parsed_document.author == "Fixture Author"
    assert parsed_document.description == "Alice's fixture description."
    assert parsed_document.cover_extension == ".svg"
    assert parsed_document.cover_bytes is not None
    assert b"Fixture Cover" in parsed_document.cover_bytes
    assert parsed_document.sections


def test_parse_epub_bytes_normalizes_relative_spine_paths(
    epub_relative_fixture_bytes: bytes,
) -> None:
    parser_module = import_module("app.parsers.epub")
    parser_module = reload(parser_module)

    sections = parser_module.parse_epub_bytes(epub_relative_fixture_bytes)

    assert sections
    assert sections[0].title == "Escaped Chapter"
    assert "Alice follows a relative EPUB path." in sections[0].text


def test_parse_epub_rejects_high_compression_ratio(monkeypatch: pytest.MonkeyPatch) -> None:
    parser_module = import_module("app.parsers.epub")
    parser_module = reload(parser_module)
    monkeypatch.setattr(parser_module.settings, "epub_max_compression_ratio", 10.0)

    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("META-INF/container.xml", b"A" * 100_000)

    with pytest.raises(ValueError, match="compression ratio"):
        parser_module.parse_epub_document(buffer.getvalue())


def test_parse_epub_counts_repeated_member_reads_against_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser_module = import_module("app.parsers.epub")
    parser_module = reload(parser_module)
    monkeypatch.setattr(parser_module.settings, "epub_max_uncompressed_bytes", 15)
    monkeypatch.setattr(parser_module.settings, "epub_max_compression_ratio", 10_000.0)

    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("one.txt", b"1234567890")

    with ZipFile(BytesIO(buffer.getvalue())) as archive:
        reader = parser_module._BoundedArchiveReader(archive)
        assert reader.read("one.txt") == b"1234567890"
        with pytest.raises(ValueError, match="parsing exceeded"):
            reader.read("one.txt")


def test_parse_pdf_bytes_returns_page_sections(pdf_fixture_bytes: bytes) -> None:
    parser_module = import_module("app.parsers.pdf")
    parser_module = reload(parser_module)

    sections = parser_module.parse_pdf_bytes(pdf_fixture_bytes)

    assert sections
    assert sections[0].title == "Page 1"
    assert "Alice" in sections[0].text


def test_import_document_parses_epub_into_sections_and_chunks(
    tmp_path, monkeypatch, epub_fixture_bytes: bytes
) -> None:
    config_module = import_module("app.config")

    monkeypatch.setattr(
        config_module.settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}"
    )
    monkeypatch.setattr(config_module.settings, "source_root", tmp_path / "data" / "source")

    db_module = import_module("app.db")
    models_module = import_module("app.models")
    documents_module = import_module("app.services.documents")

    db_module = reload(db_module)
    models_module = reload(models_module)
    reload(import_module("app.models.document"))
    reload(import_module("app.models.document_profile"))
    reload(import_module("app.models.document_progress"))
    reload(import_module("app.models.section"))
    reload(import_module("app.models.text_chunk"))
    documents_module = reload(documents_module)
    documents_module.init_database()

    upload_path = tmp_path / "book.epub"
    upload = UploadFile(
        file=upload_path.open("w+b"),
        filename="book.epub",
        headers=Headers({"content-type": "application/epub+zip"}),
    )
    upload.file.write(epub_fixture_bytes)
    upload.file.seek(0)

    document = documents_module.import_document(upload)

    with db_module.session_scope() as session:
        section_model = import_module("app.models.section").Section
        chunk_model = import_module("app.models.text_chunk").TextChunk

        sections = session.query(section_model).all()
        chunks = session.query(chunk_model).order_by(chunk_model.position).all()

    assert document.format == "epub"
    assert len(sections) >= 1
    assert sections[0].title
    assert "Alice" in sections[0].text
    assert chunks


def test_import_document_parses_pdf_into_sections_and_chunks(
    tmp_path, monkeypatch, pdf_fixture_bytes: bytes
) -> None:
    config_module = import_module("app.config")

    monkeypatch.setattr(
        config_module.settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}"
    )
    monkeypatch.setattr(config_module.settings, "source_root", tmp_path / "data" / "source")

    db_module = import_module("app.db")
    models_module = import_module("app.models")
    documents_module = import_module("app.services.documents")

    db_module = reload(db_module)
    models_module = reload(models_module)
    reload(import_module("app.models.document"))
    reload(import_module("app.models.document_profile"))
    reload(import_module("app.models.document_progress"))
    reload(import_module("app.models.section"))
    reload(import_module("app.models.text_chunk"))
    documents_module = reload(documents_module)
    documents_module.init_database()

    upload_path = tmp_path / "book.pdf"
    upload = UploadFile(
        file=upload_path.open("w+b"),
        filename="book.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )
    upload.file.write(pdf_fixture_bytes)
    upload.file.seek(0)

    document = documents_module.import_document(upload)

    with db_module.session_scope() as session:
        section_model = import_module("app.models.section").Section
        chunk_model = import_module("app.models.text_chunk").TextChunk

        sections = session.query(section_model).all()
        chunks = session.query(chunk_model).order_by(chunk_model.position).all()

    assert document.format == "pdf"
    assert len(sections) >= 1
    assert sections[0].title == "Page 1"
    assert "Alice" in sections[0].text
    assert chunks
