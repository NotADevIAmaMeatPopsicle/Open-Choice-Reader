from pathlib import Path

from app.parsers.base import ParsedDocument, ParsedSection
from app.services import book_metadata


def test_parse_project_gutenberg_top_books_extracts_ranked_ids() -> None:
    html = """
    <html>
      <body>
        <h2>Top 100 EBooks yesterday</h2>
        <ol>
          <li><a href="/ebooks/84">Frankenstein; or, the modern prometheus by Mary Wollstonecraft Shelley (5063)</a></li>
          <li><a href="/ebooks/1342">Pride and Prejudice by Jane Austen (4665)</a></li>
          <li><a href="/ebooks/2701">Moby Dick; Or, The Whale by Herman Melville (4640)</a></li>
        </ol>
        <h2>Top 100 Authors yesterday</h2>
      </body>
    </html>
    """

    books = book_metadata.parse_project_gutenberg_top_books(html)

    assert [(book.rank, book.gutenberg_id) for book in books] == [(1, 84), (2, 1342), (3, 2701)]
    assert books[0].label.startswith("Frankenstein")


def test_parse_project_gutenberg_download_asset_prefers_image_epub() -> None:
    html = """
    <html>
      <body>
        <a href="/ebooks/1259.epub.noimages" type="application/epub+zip">EPUB</a>
        <a href="/ebooks/1259.epub.images" type="application/epub+zip">EPUB with images</a>
        <a href="/ebooks/1259.txt.utf-8" type="text/plain; charset=utf-8">Plain text</a>
      </body>
    </html>
    """

    asset = book_metadata.parse_project_gutenberg_download_asset(html, book_id=1259)

    assert asset is not None
    assert asset.url == "https://www.gutenberg.org/ebooks/1259.epub.images"
    assert asset.extension == ".epub"


def test_parse_top_book_label_splits_title_and_author() -> None:
    title, author = book_metadata.parse_top_book_label(
        "Pride and Prejudice by Jane Austen (4665)"
    )

    assert title == "Pride and Prejudice"
    assert author == "Jane Austen"


def test_enrich_parsed_document_uses_exact_gutendex_match_for_gutenberg_filename(monkeypatch) -> None:
    monkeypatch.setattr(book_metadata.settings, "metadata_enrichment_enabled", True)
    monkeypatch.setattr(
        book_metadata,
        "fetch_gutendex_book",
        lambda book_id: {
            "id": book_id,
            "title": "Frankenstein; or, the modern prometheus",
            "authors": [{"name": "Shelley, Mary Wollstonecraft"}],
            "summaries": ["Victor Frankenstein creates a creature and regrets it."],
            "formats": {"image/jpeg": "https://example.test/frankenstein.jpg"},
        },
    )
    monkeypatch.setattr(book_metadata, "fetch_binary_asset", lambda _url: (b"cover-bytes", ".jpg"))

    resolution = book_metadata.enrich_parsed_document(
        ParsedDocument(sections=[ParsedSection(title="Chapter 1", text="Text body")]),
        filename=Path("gutenberg-84-frankenstein.epub"),
        origin_path=Path("gutenberg-84-frankenstein.epub"),
    )

    assert resolution.parsed_document.title == "Frankenstein; or, the modern prometheus"
    assert resolution.parsed_document.author == "Shelley, Mary Wollstonecraft"
    assert resolution.parsed_document.description == "Victor Frankenstein creates a creature and regrets it."
    assert resolution.parsed_document.cover_bytes == b"cover-bytes"
    assert resolution.parsed_document.cover_extension == ".jpg"
    assert resolution.metadata_source == "gutendex"
    assert resolution.metadata_source_id == "84"


def test_enrich_parsed_document_falls_back_to_open_library_then_gutendex(monkeypatch) -> None:
    monkeypatch.setattr(book_metadata.settings, "metadata_enrichment_enabled", True)
    monkeypatch.setattr(
        book_metadata,
        "search_open_library",
        lambda title, author: {
            "title": title,
            "author_name": [author],
            "id_project_gutenberg": [1342],
            "cover_i": 987,
            "key": "/works/OL123W",
        },
    )
    monkeypatch.setattr(
        book_metadata,
        "fetch_gutendex_book",
        lambda book_id: {
            "id": book_id,
            "title": "Pride and Prejudice",
            "authors": [{"name": "Austen, Jane"}],
            "summaries": ["Elizabeth Bennet navigates class, pride, and affection."],
            "formats": {"image/jpeg": "https://example.test/pride.jpg"},
        },
    )
    monkeypatch.setattr(book_metadata, "fetch_binary_asset", lambda _url: (b"pride-cover", ".jpg"))

    resolution = book_metadata.enrich_parsed_document(
        ParsedDocument(
            sections=[ParsedSection(title="Section", text="Text body")],
            title="Pride and Prejudice",
            author="Jane Austen",
        ),
        filename=Path("pride.epub"),
        origin_path=None,
    )

    assert resolution.parsed_document.title == "Pride and Prejudice"
    assert resolution.parsed_document.author == "Austen, Jane"
    assert resolution.parsed_document.description == "Elizabeth Bennet navigates class, pride, and affection."
    assert resolution.parsed_document.cover_bytes == b"pride-cover"
    assert resolution.metadata_source == "gutendex"
    assert resolution.metadata_source_id == "1342"


def test_select_download_asset_prefers_epub() -> None:
    asset = book_metadata.select_download_asset(
        {
            "formats": {
                "text/plain; charset=utf-8": "https://example.test/book.txt",
                "application/epub+zip": "https://example.test/book.epub",
            }
        }
    )

    assert asset is not None
    assert asset.url == "https://example.test/book.epub"
    assert asset.extension == ".epub"
