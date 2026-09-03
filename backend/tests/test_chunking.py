from importlib import import_module, reload
from pathlib import Path

from starlette.datastructures import Headers, UploadFile


def test_parse_plain_text_extracts_markdown_heading() -> None:
    parser_module = import_module("app.parsers.plain_text")
    parser_module = reload(parser_module)

    sections = parser_module.parse_plain_text("# Chapter One\n\nHello world.", "md")

    assert len(sections) == 1
    assert sections[0].title == "Chapter One"
    assert sections[0].text == "Hello world."


def test_chunk_paragraphs_keeps_short_passages_together() -> None:
    chunking_module = import_module("app.services.chunking")
    chunking_module = reload(chunking_module)

    chunks = chunking_module.chunk_paragraphs("Alice reads. Then Alice pauses.")

    assert chunks == ["Alice reads. Then Alice pauses."]


def test_chunk_paragraphs_keeps_common_abbreviations_with_sentence() -> None:
    chunking_module = import_module("app.services.chunking")
    chunking_module = reload(chunking_module)

    chunks = chunking_module.chunk_paragraphs("Dr. Smith reads. Then Alice pauses.")

    assert chunks == ["Dr. Smith reads. Then Alice pauses."]


def test_chunk_paragraphs_handles_quoted_prose() -> None:
    chunking_module = import_module("app.services.chunking")
    chunking_module = reload(chunking_module)

    chunks = chunking_module.chunk_paragraphs('"Alice reads." Then Alice pauses.')

    assert chunks == ['"Alice reads." Then Alice pauses.']


def test_chunk_paragraphs_splits_long_passages_into_multiple_windows() -> None:
    chunking_module = import_module("app.services.chunking")
    chunking_module = reload(chunking_module)

    long_passage = " ".join(
        [
            "Alice reads the first part carefully."
            " Then Alice pauses and reflects on the argument."
            " The next idea arrives with more detail and more texture."
        ]
        * 14
    )

    chunks = chunking_module.chunk_paragraphs(long_passage)

    assert len(chunks) >= 2
    assert all(chunk.endswith((".", "!", "?")) for chunk in chunks)
    assert all(len(chunk.split()) <= 260 for chunk in chunks)


def test_import_document_creates_sections_and_chunks_for_markdown(
    tmp_path: Path, monkeypatch
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

    upload_path = tmp_path / "chapter.md"
    upload = UploadFile(
        file=upload_path.open("w+b"),
        filename="chapter.md",
        headers=Headers({"content-type": "text/markdown"}),
    )
    upload.file.write(b"# Chapter One\n\nAlice reads. Then Alice pauses.")
    upload.file.seek(0)

    document = documents_module.import_document(upload)

    with db_module.session_scope() as session:
        section_model = import_module("app.models.section").Section
        chunk_model = import_module("app.models.text_chunk").TextChunk

        sections = session.query(section_model).all()
        chunks = session.query(chunk_model).order_by(chunk_model.position).all()

    assert document.title == "Chapter One"
    assert len(sections) == 1
    assert sections[0].document_id == document.id
    assert sections[0].title == "Chapter One"
    assert sections[0].text == "Alice reads. Then Alice pauses."
    assert [chunk.text for chunk in chunks] == ["Alice reads. Then Alice pauses."]


def test_import_document_creates_sections_and_chunks_for_txt(
    tmp_path: Path, monkeypatch
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

    upload_path = tmp_path / "chapter.txt"
    upload = UploadFile(
        file=upload_path.open("w+b"),
        filename="chapter.txt",
        headers=Headers({"content-type": "text/plain"}),
    )
    upload.file.write(b"Dr. Smith reads. Then Alice pauses.")
    upload.file.seek(0)

    document = documents_module.import_document(upload)

    with db_module.session_scope() as session:
        section_model = import_module("app.models.section").Section
        chunk_model = import_module("app.models.text_chunk").TextChunk

        sections = session.query(section_model).all()
        chunks = session.query(chunk_model).order_by(chunk_model.position).all()

    assert document.title == "chapter"
    assert len(sections) == 1
    assert sections[0].document_id == document.id
    assert sections[0].title is None
    assert sections[0].text == "Dr. Smith reads. Then Alice pauses."
    assert [chunk.text for chunk in chunks] == ["Dr. Smith reads. Then Alice pauses."]
