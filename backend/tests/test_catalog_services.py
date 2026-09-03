import app.services.catalogs as catalogs


def test_search_gutenberg_catalog_normalizes_results(monkeypatch) -> None:
    monkeypatch.setattr(
        catalogs.book_metadata,
        "fetch_json",
        lambda url: {
            "results": [
                {
                    "id": 84,
                    "title": "Frankenstein; or, the modern prometheus",
                    "authors": [{"name": "Shelley, Mary Wollstonecraft"}],
                    "summaries": ["A scientist creates a monster and regrets it."],
                    "languages": ["en"],
                    "copyright": False,
                    "formats": {
                        "application/epub+zip": "https://www.gutenberg.org/ebooks/84.epub3.images",
                        "image/jpeg": "https://www.gutenberg.org/cache/epub/84/pg84.cover.medium.jpg",
                    },
                }
            ]
        },
    )

    results = catalogs.search_gutenberg_catalog("frankenstein", limit=5)

    assert results == [
        catalogs.CatalogResultRecord(
            id="84",
            source="gutenberg",
            source_name="Project Gutenberg",
            title="Frankenstein; or, the modern prometheus",
            author="Shelley, Mary Wollstonecraft",
            summary="A scientist creates a monster and regrets it.",
            cover_url="https://www.gutenberg.org/cache/epub/84/pg84.cover.medium.jpg",
            detail_url="https://www.gutenberg.org/ebooks/84",
            download_format="epub",
            language="en",
            importable=True,
        )
    ]


def test_search_standard_ebooks_catalog_builds_detail_results(monkeypatch) -> None:
    listing_html = """
    <html xmlns="http://www.w3.org/1999/xhtml">
      <body>
        <ol class="ebooks-list grid">
          <li typeof="schema:Book" about="/ebooks/mary-shelley/frankenstein">
            <p><a href="/ebooks/mary-shelley/frankenstein"><span>Frankenstein</span></a></p>
            <p class="author"><a href="https://standardebooks.org/ebooks/mary-shelley"><span>Mary Shelley</span></a></p>
          </li>
        </ol>
      </body>
    </html>
    """
    detail_html = """
    <?xml version="1.0" encoding="utf-8"?>
    <html xmlns="http://www.w3.org/1999/xhtml" lang="en-US">
      <head>
        <title>Frankenstein, by Mary Shelley - Free ebook download - Standard Ebooks</title>
        <meta content="Free epub ebook download of the Standard Ebooks edition of Frankenstein: A tragic scientist creates a monster in his laboratory." name="description"/>
        <meta content="https://standardebooks.org/ebooks/mary-shelley/frankenstein/downloads/cover.jpg" property="og:image"/>
      </head>
      <body>
        <a href="/ebooks/mary-shelley/frankenstein/downloads/mary-shelley_frankenstein.epub">epub</a>
      </body>
    </html>
    """

    def fake_fetch_text(url: str) -> str:
        if "query=frankenstein" in url:
            return listing_html
        if url == "https://standardebooks.org/ebooks/mary-shelley/frankenstein":
            return detail_html
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(catalogs.book_metadata, "fetch_text", fake_fetch_text)

    results = catalogs.search_standard_ebooks_catalog("frankenstein", limit=5)

    assert results == [
        catalogs.CatalogResultRecord(
            id="mary-shelley/frankenstein",
            source="standard_ebooks",
            source_name="Standard Ebooks",
            title="Frankenstein",
            author="Mary Shelley",
            summary="A tragic scientist creates a monster in his laboratory.",
            cover_url="https://standardebooks.org/ebooks/mary-shelley/frankenstein/downloads/cover.jpg",
            detail_url="https://standardebooks.org/ebooks/mary-shelley/frankenstein",
            download_format="epub",
            language="en-US",
            importable=True,
        )
    ]


def test_search_open_library_catalog_filters_for_public_archive_results(monkeypatch) -> None:
    def fake_fetch_json(url: str) -> dict:
        if "openlibrary.org/search.json" in url:
            return {
                "docs": [
                    {
                        "key": "/works/OL450822W",
                        "title": "Frankenstein",
                        "author_name": ["Mary Shelley"],
                        "cover_i": 12345,
                        "has_fulltext": True,
                        "ebook_access": "public",
                        "ia": ["frankensteinormo00shel"],
                    },
                    {
                        "key": "/works/OL999999W",
                        "title": "Not Importable",
                        "author_name": ["Someone Else"],
                        "cover_i": 99999,
                        "has_fulltext": False,
                        "ebook_access": "borrowable",
                        "ia": [],
                    },
                ]
            }
        if url == "https://archive.org/metadata/frankensteinormo00shel":
            return {
                "metadata": {
                    "identifier": "frankensteinormo00shel",
                    "title": "Frankenstein, or, The modern Prometheus",
                    "creator": ["Shelley, Mary Wollstonecraft, 1797-1851"],
                    "description": "Includes bibliographical references.",
                },
                "files": [
                    {"name": "frankensteinormo00shel.epub"},
                    {"name": "__ia_thumb.jpg"},
                ],
            }
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(catalogs.book_metadata, "fetch_json", fake_fetch_json)

    results = catalogs.search_open_library_catalog("frankenstein", limit=5)

    assert results == [
        catalogs.CatalogResultRecord(
            id="frankensteinormo00shel",
            source="openlibrary",
            source_name="Open Library / Internet Archive",
            title="Frankenstein",
            author="Mary Shelley",
            summary="Includes bibliographical references.",
            cover_url="https://covers.openlibrary.org/b/id/12345-L.jpg",
            detail_url="https://openlibrary.org/works/OL450822W",
            download_format="epub",
            language=None,
            importable=True,
        )
    ]


def test_import_standard_ebooks_item_appends_source_download_query_parameter(monkeypatch) -> None:
    monkeypatch.setattr(
        catalogs,
        "_fetch_standard_ebooks_detail",
        lambda path: {
            "title": "Frankenstein",
            "author": "Mary Shelley",
            "summary": "A tragic scientist creates a monster in his laboratory.",
            "cover_url": "https://standardebooks.org/ebooks/mary-shelley/frankenstein/downloads/cover.jpg",
            "language": "en-US",
            "asset": catalogs.DownloadAsset(
                url="https://standardebooks.org/ebooks/mary-shelley/frankenstein/downloads/mary-shelley_frankenstein.epub",
                media_type="application/epub+zip",
                extension=".epub",
            ),
        },
    )

    seen: dict[str, str] = {}

    monkeypatch.setattr(
        catalogs.book_metadata,
        "fetch_remote_bytes",
        lambda url: seen.setdefault("url", url) or b"PKdemo",
    )
    monkeypatch.setattr(catalogs.book_metadata, "fetch_binary_asset", lambda _url: (None, None))
    monkeypatch.setattr(catalogs, "import_external_document", lambda **kwargs: kwargs)

    result = catalogs.import_catalog_item("standard_ebooks", "mary-shelley/frankenstein")

    assert result["filename"] == "mary-shelley_frankenstein.epub"
    assert seen["url"].endswith("?source=download")


def test_import_open_library_item_prefers_pdf_over_epub_for_import_safety(monkeypatch) -> None:
    monkeypatch.setattr(
        catalogs.book_metadata,
        "fetch_json",
        lambda url: {
            "metadata": {
                "identifier": "frankensteinormo00shel_8",
                "title": "Frankenstein",
                "creator": ["Shelley, Mary Wollstonecraft"],
                "description": "Public-domain scan.",
            },
            "files": [
                {"name": "frankensteinormo00shel_8.epub"},
                {"name": "frankensteinormo00shel_8.pdf"},
                {"name": "__ia_thumb.jpg"},
            ],
        },
    )
    monkeypatch.setattr(catalogs.book_metadata, "fetch_binary_asset", lambda _url: (None, None))

    seen: dict[str, str] = {}
    monkeypatch.setattr(
        catalogs.book_metadata,
        "fetch_remote_bytes",
        lambda url: seen.setdefault("url", url) or b"%PDF-demo",
    )
    monkeypatch.setattr(catalogs, "import_external_document", lambda **kwargs: kwargs)

    result = catalogs.import_catalog_item("openlibrary", "frankensteinormo00shel_8")

    assert result["filename"] == "frankensteinormo00shel_8.pdf"
    assert seen["url"].endswith(".pdf")
