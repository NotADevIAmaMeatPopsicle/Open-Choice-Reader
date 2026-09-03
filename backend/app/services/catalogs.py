from __future__ import annotations

from html import escape
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlencode, urljoin, urlparse

from app.config import settings
from app.services import book_metadata
from app.services.book_metadata import DownloadAsset, ExternalMetadata
from app.services.documents import SUPPORTED_IMPORT_FORMATS, ExternalSourceProvenance, import_external_document
from app.services.remote_fetch import fetch_remote_resource


STANDARD_EBOOKS_ROOT = "https://standardebooks.org"
GUTENBERG_ROOT = "https://www.gutenberg.org"
ARCHIVE_DOWNLOAD_ROOT = "https://archive.org/download"
ARCHIVE_DETAILS_ROOT = "https://archive.org/details"

STANDARD_EBOOKS_LISTING_PATTERN = re.compile(
    r'<li[^>]+about="(?P<path>/ebooks/[^"]+)"[^>]*>.*?'
    r'<span[^>]*?(?:property="schema:name"[^>]*?)?>(?P<title>[^<]+)</span>.*?'
    r'(?:<p class="author"[^>]*>.*?<span[^>]*?(?:property="schema:name"[^>]*?)?>(?P<author>[^<]+)</span>)?',
    re.IGNORECASE | re.DOTALL,
)
STANDARD_EBOOKS_TITLE_PATTERN = re.compile(
    r"<title>(?P<title>.+?)(?:,\s*by\s*(?P<author>.+?))?\s*-\s*Free ebook download",
    re.IGNORECASE | re.DOTALL,
)
STANDARD_EBOOKS_META_PATTERN_TEMPLATE = r'<meta content="(?P<value>[^"]+)" {attribute_name}="{attribute_value}"'
STANDARD_EBOOKS_EPUB_PATTERN = re.compile(
    r'href="(?P<href>/ebooks/[^"]+/downloads/[^"]+\.epub)"',
    re.IGNORECASE,
)


@dataclass(slots=True)
class CatalogSourceRecord:
    id: str
    name: str
    description: str
    supports_search: bool
    supports_browse: bool


@dataclass(slots=True)
class CatalogResultRecord:
    id: str
    source: str
    source_name: str
    title: str
    author: str | None
    summary: str | None
    cover_url: str | None
    detail_url: str
    download_format: str | None
    language: str | None
    importable: bool


@dataclass(slots=True)
class RemoteAssetRecord:
    requested_url: str
    final_url: str
    content_type: str
    filename: str | None
    body: bytes


@dataclass(slots=True)
class ArticleSnapshotRecord:
    title: str | None
    author: str | None
    summary: str | None
    cleaned_html: str


CATALOG_SOURCES = [
    CatalogSourceRecord(
        id="gutenberg",
        name="Project Gutenberg",
        description="Public-domain ebooks discovered through Gutenberg and Gutendex.",
        supports_search=True,
        supports_browse=True,
    ),
    CatalogSourceRecord(
        id="standard_ebooks",
        name="Standard Ebooks",
        description="Carefully produced public-domain ebook editions from Standard Ebooks.",
        supports_search=True,
        supports_browse=True,
    ),
    CatalogSourceRecord(
        id="openlibrary",
        name="Open Library / Internet Archive",
        description="Public full-text works discovered in Open Library and imported from Internet Archive.",
        supports_search=True,
        supports_browse=False,
    ),
]


def list_catalog_sources() -> list[CatalogSourceRecord]:
    return CATALOG_SOURCES


def browse_gutenberg_catalog(limit: int = 12) -> list[CatalogResultRecord]:
    results: list[CatalogResultRecord] = []
    for top_book in book_metadata.fetch_project_gutenberg_top_books(limit=limit):
        record = book_metadata.fetch_gutendex_book(top_book.gutenberg_id)
        if record is not None:
            normalized = _normalize_gutendex_record(record)
            if normalized is not None:
                results.append(normalized)
                continue

        asset = book_metadata.fetch_project_gutenberg_download_asset(top_book.gutenberg_id)
        title, author = book_metadata.parse_top_book_label(top_book.label)
        if asset is None:
            continue
        results.append(
            CatalogResultRecord(
                id=str(top_book.gutenberg_id),
                source="gutenberg",
                source_name="Project Gutenberg",
                title=title,
                author=author,
                summary=None,
                cover_url=None,
                detail_url=f"{GUTENBERG_ROOT}/ebooks/{top_book.gutenberg_id}",
                download_format=_extension_to_format(asset.extension),
                language=None,
                importable=True,
            )
        )
    return results[:limit]


def search_gutenberg_catalog(query: str, limit: int = 12) -> list[CatalogResultRecord]:
    payload = book_metadata.fetch_json(f"{settings.gutendex_api_base}?{urlencode({'search': query})}")
    results: list[CatalogResultRecord] = []
    for record in payload.get("results") or []:
        normalized = _normalize_gutendex_record(record)
        if normalized is None:
            continue
        results.append(normalized)
        if len(results) >= limit:
            break
    return results


def browse_standard_ebooks_catalog(limit: int = 12, sort: str = "new") -> list[CatalogResultRecord]:
    params = {"sort": sort, "per-page": limit, "view": "grid"}
    listing_url = f"{STANDARD_EBOOKS_ROOT}/ebooks?{urlencode(params)}"
    listing_html = book_metadata.fetch_text(listing_url)
    return _build_standard_ebooks_results(listing_html, limit=limit)


def search_standard_ebooks_catalog(query: str, limit: int = 12) -> list[CatalogResultRecord]:
    params = {"query": query, "per-page": limit, "view": "grid"}
    listing_url = f"{STANDARD_EBOOKS_ROOT}/ebooks?{urlencode(params)}"
    listing_html = book_metadata.fetch_text(listing_url)
    return _build_standard_ebooks_results(listing_html, limit=limit)


def search_open_library_catalog(query: str, limit: int = 12) -> list[CatalogResultRecord]:
    params = {
        "q": query,
        "fields": "key,title,author_name,cover_i,has_fulltext,ebook_access,ia,availability,language",
        "limit": max(limit * 3, 12),
    }
    payload = book_metadata.fetch_json(f"{settings.open_library_search_url}?{urlencode(params)}")
    results: list[CatalogResultRecord] = []

    for record in payload.get("docs") or []:
        if not _is_open_library_record_importable(record):
            continue

        archive_identifier, asset, metadata = _resolve_open_library_archive_item(record)
        if archive_identifier is None or asset is None:
            continue

        cover_identifier = record.get("cover_i")
        cover_url = (
            f"{settings.open_library_cover_base}/{cover_identifier}-L.jpg"
            if cover_identifier is not None
            else _build_archive_cover_url(archive_identifier, metadata.get("files") or [])
        )
        results.append(
            CatalogResultRecord(
                id=archive_identifier,
                source="openlibrary",
                source_name="Open Library / Internet Archive",
                title=_safe_text(record.get("title")) or _safe_text(metadata.get("metadata", {}).get("title")) or archive_identifier,
                author=_extract_open_library_author(record) or _coerce_archive_author(metadata.get("metadata", {}).get("creator")),
                summary=_extract_archive_description(metadata.get("metadata", {}).get("description")),
                cover_url=cover_url,
                detail_url=f"https://openlibrary.org{record.get('key')}" if record.get("key") else f"{ARCHIVE_DETAILS_ROOT}/{archive_identifier}",
                download_format=_extension_to_format(asset.extension),
                language=_extract_open_library_language(record),
                importable=True,
            )
        )
        if len(results) >= limit:
            break

    return results


def import_catalog_item(source: str, catalog_id: str, *, owner_user_id: int | None = None):
    if source == "gutenberg":
        return _import_gutenberg_item(catalog_id, owner_user_id=owner_user_id)
    if source == "standard_ebooks":
        return _import_standard_ebooks_item(catalog_id, owner_user_id=owner_user_id)
    if source == "openlibrary":
        return _import_open_library_item(catalog_id, owner_user_id=owner_user_id)
    raise ValueError(f"Unsupported catalog source '{source}'")


def import_url_item(url: str, *, owner_user_id: int | None = None):
    normalized_url = _normalize_url(url)
    remote_asset = _fetch_remote_asset(normalized_url)
    filename = remote_asset.filename or _filename_from_url(remote_asset.final_url)
    site_name = _site_name_from_url(remote_asset.final_url)

    if filename:
        file_format = _normalized_extension(filename)
        if file_format in SUPPORTED_IMPORT_FORMATS:
            if file_format != "html" and _looks_like_html_response(
                content_type=remote_asset.content_type,
                body=remote_asset.body,
            ):
                raise ValueError(
                    f"That URL returned HTML instead of a raw .{file_format} file. Try the page URL as an article import instead."
                )

            return import_external_document(
                filename=filename,
                file_bytes=remote_asset.body,
                metadata_hint=None,
                source_provenance=ExternalSourceProvenance(
                    provider="url",
                    provider_id=remote_asset.final_url,
                    provider_name="Direct URL import",
                    provider_url=remote_asset.final_url,
                    source_url=remote_asset.final_url,
                    source_site_name=site_name,
                    import_mode="direct_url",
                ),
                owner_user_id=owner_user_id,
            )

    inferred_extension = _infer_extension_from_content_type(remote_asset.content_type)
    if inferred_extension and inferred_extension in SUPPORTED_IMPORT_FORMATS and inferred_extension != "html":
        direct_filename = filename or f"imported{_extension_suffix(inferred_extension)}"
        return import_external_document(
            filename=direct_filename,
            file_bytes=remote_asset.body,
            metadata_hint=None,
            source_provenance=ExternalSourceProvenance(
                provider="url",
                provider_id=remote_asset.final_url,
                provider_name="Direct URL import",
                provider_url=remote_asset.final_url,
                source_url=remote_asset.final_url,
                source_site_name=site_name,
                import_mode="direct_url",
            ),
            owner_user_id=owner_user_id,
        )

    if not _looks_like_html_response(content_type=remote_asset.content_type, body=remote_asset.body):
        raise ValueError("The URL did not resolve to a supported document or readable article page")

    article_snapshot = _extract_article_snapshot(
        remote_asset.body.decode("utf-8", errors="replace"),
        remote_asset.final_url,
    )
    article_title = article_snapshot.title or _fallback_title_from_url(remote_asset.final_url)
    article_filename = f"{_slugify_filename(article_title)}.html"
    return import_external_document(
        filename=article_filename,
        file_bytes=article_snapshot.cleaned_html.encode("utf-8"),
        metadata_hint=ExternalMetadata(
            title=article_title,
            author=article_snapshot.author,
            description=article_snapshot.summary,
            metadata_source="article_url",
            metadata_source_id=remote_asset.final_url,
            exact_match=True,
        ),
        source_provenance=ExternalSourceProvenance(
            provider="web",
            provider_id=remote_asset.final_url,
            provider_name="Article import",
            provider_url=remote_asset.final_url,
            source_url=remote_asset.final_url,
            source_site_name=site_name,
            import_mode="article_url",
        ),
        owner_user_id=owner_user_id,
    )


def import_pasted_text_item(
    *,
    title: str,
    body: str,
    author: str | None,
    source_url: str | None,
    owner_user_id: int | None = None,
):
    normalized_title = title.strip()
    if not normalized_title:
        raise ValueError("Pasted text imports need a title")

    normalized_body = body.strip()
    if not normalized_body:
        raise ValueError("Pasted text imports need body text")

    normalized_source_url = _normalize_url(source_url) if source_url else None
    site_name = _site_name_from_url(normalized_source_url) if normalized_source_url else None
    snapshot = _build_pasted_text_snapshot(
        title=normalized_title,
        body=normalized_body,
        author=author,
        source_url=normalized_source_url,
        source_site_name=site_name,
    )
    filename = f"{_slugify_filename(normalized_title)}.md"

    return import_external_document(
        filename=filename,
        file_bytes=snapshot.encode("utf-8"),
        metadata_hint=ExternalMetadata(
            title=normalized_title,
            author=author.strip() if isinstance(author, str) and author.strip() else None,
            description=normalized_body[:240],
            metadata_source="pasted_text",
            metadata_source_id=normalized_source_url or normalized_title,
            exact_match=True,
        ),
        source_provenance=ExternalSourceProvenance(
            provider="manual",
            provider_id=normalized_source_url or normalized_title,
            provider_name="Pasted text",
            provider_url=normalized_source_url,
            source_url=normalized_source_url,
            source_site_name=site_name,
            import_mode="pasted_text",
        ),
        owner_user_id=owner_user_id,
    )


def _normalize_gutendex_record(record: dict) -> CatalogResultRecord | None:
    asset = book_metadata.select_download_asset(record)
    if asset is None:
        return None

    formats = record.get("formats") or {}
    summaries = record.get("summaries") or []
    languages = record.get("languages") or []
    return CatalogResultRecord(
        id=str(record.get("id")),
        source="gutenberg",
        source_name="Project Gutenberg",
        title=_safe_text(record.get("title")) or "Untitled",
        author=book_metadata.join_author_names(record.get("authors") or []),
        summary=_safe_text(summaries[0]) if summaries else None,
        cover_url=_safe_text(formats.get("image/jpeg")) or _safe_text(formats.get("image/png")),
        detail_url=f"{GUTENBERG_ROOT}/ebooks/{record.get('id')}",
        download_format=_extension_to_format(asset.extension),
        language=_safe_text(languages[0]) if languages else None,
        importable=True,
    )


def _build_standard_ebooks_results(listing_html: str, *, limit: int) -> list[CatalogResultRecord]:
    results: list[CatalogResultRecord] = []
    for path, fallback_title, fallback_author in _parse_standard_ebooks_listing(listing_html)[:limit]:
        detail = _fetch_standard_ebooks_detail(path)
        results.append(
            CatalogResultRecord(
                id=path.removeprefix("/ebooks/"),
                source="standard_ebooks",
                source_name="Standard Ebooks",
                title=detail["title"] or fallback_title or path.rsplit("/", 1)[-1].replace("-", " ").title(),
                author=detail["author"] or fallback_author,
                summary=detail["summary"],
                cover_url=detail["cover_url"],
                detail_url=f"{STANDARD_EBOOKS_ROOT}{path}",
                download_format=_extension_to_format(detail["asset"].extension) if detail["asset"] is not None else None,
                language=detail["language"],
                importable=detail["asset"] is not None,
            )
        )
    return results


def _parse_standard_ebooks_listing(html: str) -> list[tuple[str, str | None, str | None]]:
    seen_paths: set[str] = set()
    results: list[tuple[str, str | None, str | None]] = []
    for match in STANDARD_EBOOKS_LISTING_PATTERN.finditer(html):
        path = match.group("path")
        if path in seen_paths:
            continue
        seen_paths.add(path)
        results.append(
            (
                path,
                _strip_html_text(match.group("title")),
                _strip_html_text(match.group("author")),
            )
        )
    return results


def _fetch_standard_ebooks_detail(path: str) -> dict:
    detail_url = f"{STANDARD_EBOOKS_ROOT}{path}"
    html = book_metadata.fetch_text(detail_url)

    title_match = STANDARD_EBOOKS_TITLE_PATTERN.search(html)
    meta_description = _search_meta(html, attribute_name="name", attribute_value="description")
    og_image = _search_meta(html, attribute_name="property", attribute_value="og:image")
    language_match = re.search(r'<html[^>]+lang="(?P<lang>[^"]+)"', html, re.IGNORECASE)
    download_asset = _select_standard_ebooks_asset(html)

    description = _clean_standard_ebooks_description(meta_description)
    return {
        "title": _strip_html_text(title_match.group("title")) if title_match else None,
        "author": _strip_html_text(title_match.group("author")) if title_match else None,
        "summary": description,
        "cover_url": og_image,
        "language": language_match.group("lang") if language_match else None,
        "asset": download_asset,
    }


def _select_standard_ebooks_asset(html: str) -> DownloadAsset | None:
    hrefs = [match.group("href") for match in STANDARD_EBOOKS_EPUB_PATTERN.finditer(html)]
    if not hrefs:
        return None

    def preferred_order(href: str) -> int:
        if href.endswith(".epub") and not href.endswith(".kepub.epub") and "_advanced." not in href:
            return 0
        if href.endswith(".kepub.epub"):
            return 1
        return 2

    selected_href = sorted(hrefs, key=preferred_order)[0]
    return DownloadAsset(
        url=urljoin(f"{STANDARD_EBOOKS_ROOT}/", selected_href.lstrip("/")),
        media_type="application/epub+zip",
        extension=".epub",
    )


def _clean_standard_ebooks_description(description: str | None) -> str | None:
    if not description:
        return None
    if ": " in description:
        return description.split(": ", 1)[1].strip()
    return description.strip()


def _is_open_library_record_importable(record: dict) -> bool:
    identifiers = record.get("ia") or []
    if not identifiers:
        return False
    ebook_access = str(record.get("ebook_access") or "").lower()
    return ebook_access == "public" or bool(record.get("has_fulltext"))


def _resolve_open_library_archive_item(record: dict) -> tuple[str | None, DownloadAsset | None, dict]:
    for identifier in record.get("ia") or []:
        metadata = book_metadata.fetch_json(f"https://archive.org/metadata/{identifier}")
        asset = _select_archive_download_asset(identifier, metadata.get("files") or [])
        if asset is not None:
            return identifier, asset, metadata
    return None, None, {}


def _select_archive_download_asset(identifier: str, files: list[dict]) -> DownloadAsset | None:
    preferences = (
        (".pdf", "application/pdf"),
        (".epub", "application/epub+zip"),
        (".txt", "text/plain"),
    )
    file_names = [str(file_record.get("name")) for file_record in files if file_record.get("name")]
    for suffix, media_type in preferences:
        for name in file_names:
            if not name.endswith(suffix):
                continue
            return DownloadAsset(
                url=f"{ARCHIVE_DOWNLOAD_ROOT}/{identifier}/{name}",
                media_type=media_type,
                extension=suffix,
            )
    return None


def _build_archive_cover_url(identifier: str, files: list[dict]) -> str | None:
    for file_record in files:
        name = str(file_record.get("name") or "")
        if name == "__ia_thumb.jpg":
            return f"{ARCHIVE_DOWNLOAD_ROOT}/{identifier}/{name}"
    return None


def _extract_archive_description(description_value) -> str | None:
    if isinstance(description_value, list):
        for entry in description_value:
            text = _safe_text(entry)
            if text:
                return text
        return None
    return _safe_text(description_value)


def _extract_open_library_author(record: dict) -> str | None:
    authors = record.get("author_name") or []
    return _safe_text(authors[0]) if authors else None


def _extract_open_library_language(record: dict) -> str | None:
    languages = record.get("language") or []
    if not languages:
        return None
    first_language = languages[0]
    if isinstance(first_language, dict):
        return _safe_text(first_language.get("key"))
    return _safe_text(first_language)


def _coerce_archive_author(creator_value) -> str | None:
    if isinstance(creator_value, list):
        cleaned = [_safe_text(entry) for entry in creator_value]
        filtered = [entry for entry in cleaned if entry]
        return ", ".join(filtered) if filtered else None
    return _safe_text(creator_value)


def _import_gutenberg_item(catalog_id: str, *, owner_user_id: int | None = None):
    try:
        gutenberg_id = int(catalog_id)
    except ValueError as exc:
        raise ValueError(f"Invalid Gutenberg catalog id '{catalog_id}'") from exc

    record = book_metadata.fetch_gutendex_book(gutenberg_id)
    if record is None:
        raise LookupError(f"Gutenberg title {catalog_id} was not found")

    asset = book_metadata.select_download_asset(record) or book_metadata.fetch_project_gutenberg_download_asset(gutenberg_id)
    if asset is None:
        raise LookupError(f"Gutenberg title {catalog_id} does not expose a supported download format")

    metadata_hint = book_metadata.build_external_metadata_from_gutendex(record, exact_match=True)
    filename = book_metadata.build_seed_filename(
        gutenberg_id,
        metadata_hint.title or f"gutenberg-{gutenberg_id}",
        asset.extension,
    )
    return import_external_document(
        filename=filename,
        file_bytes=book_metadata.fetch_remote_bytes(asset.url),
        metadata_hint=metadata_hint,
        source_provenance=ExternalSourceProvenance(
            provider="gutenberg",
            provider_id=str(gutenberg_id),
            provider_name="Project Gutenberg",
            provider_url=f"{GUTENBERG_ROOT}/ebooks/{gutenberg_id}",
        ),
        owner_user_id=owner_user_id,
    )


def _import_standard_ebooks_item(catalog_id: str, *, owner_user_id: int | None = None):
    normalized_id = catalog_id.strip("/")
    detail_path = f"/ebooks/{normalized_id}"
    detail = _fetch_standard_ebooks_detail(detail_path)
    asset: DownloadAsset | None = detail["asset"]
    if asset is None:
        raise LookupError(f"Standard Ebooks title '{catalog_id}' does not expose a supported EPUB download")

    cover_bytes, cover_extension = book_metadata.fetch_binary_asset(detail["cover_url"]) if detail["cover_url"] else (None, None)
    filename = PurePosixPath(asset.url).name
    return import_external_document(
        filename=filename,
        file_bytes=book_metadata.fetch_remote_bytes(_with_standard_ebooks_download_source(asset.url)),
        metadata_hint=ExternalMetadata(
            title=detail["title"],
            author=detail["author"],
            description=detail["summary"],
            cover_bytes=cover_bytes,
            cover_extension=cover_extension,
            metadata_source="standard_ebooks",
            metadata_source_id=normalized_id,
            exact_match=True,
        ),
        source_provenance=ExternalSourceProvenance(
            provider="standard_ebooks",
            provider_id=normalized_id,
            provider_name="Standard Ebooks",
            provider_url=f"{STANDARD_EBOOKS_ROOT}{detail_path}",
        ),
        owner_user_id=owner_user_id,
    )


def _import_open_library_item(catalog_id: str, *, owner_user_id: int | None = None):
    metadata = book_metadata.fetch_json(f"https://archive.org/metadata/{catalog_id}")
    asset = _select_archive_download_asset(catalog_id, metadata.get("files") or [])
    if asset is None:
        raise LookupError(f"Internet Archive item '{catalog_id}' does not expose a supported download format")

    cover_url = _build_archive_cover_url(catalog_id, metadata.get("files") or [])
    cover_bytes, cover_extension = book_metadata.fetch_binary_asset(cover_url) if cover_url else (None, None)
    archive_metadata = metadata.get("metadata", {})
    return import_external_document(
        filename=PurePosixPath(asset.url).name,
        file_bytes=book_metadata.fetch_remote_bytes(asset.url),
        metadata_hint=ExternalMetadata(
            title=_safe_text(archive_metadata.get("title")),
            author=_coerce_archive_author(archive_metadata.get("creator")),
            description=_extract_archive_description(archive_metadata.get("description")),
            cover_bytes=cover_bytes,
            cover_extension=cover_extension,
            metadata_source="internet_archive",
            metadata_source_id=catalog_id,
            exact_match=True,
        ),
        source_provenance=ExternalSourceProvenance(
            provider="openlibrary",
            provider_id=catalog_id,
            provider_name="Open Library / Internet Archive",
            provider_url=f"{ARCHIVE_DETAILS_ROOT}/{catalog_id}",
        ),
        owner_user_id=owner_user_id,
    )


def _search_meta(html: str, *, attribute_name: str, attribute_value: str) -> str | None:
    pattern = STANDARD_EBOOKS_META_PATTERN_TEMPLATE.format(
        attribute_name=attribute_name,
        attribute_value=re.escape(attribute_value),
    )
    match = re.search(pattern, html, re.IGNORECASE)
    return _safe_text(match.group("value")) if match else None


def _strip_html_text(value: str | None) -> str | None:
    if not value:
        return None
    text = re.sub(r"<[^>]+>", "", value)
    return _safe_text(text)


def _safe_text(value) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _extension_to_format(extension: str | None) -> str | None:
    if not extension:
        return None
    return extension.lstrip(".").lower() or None


def _with_standard_ebooks_download_source(url: str) -> str:
    if "source=download" in url:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}source=download"


def _normalize_url(url: str) -> str:
    normalized = url.strip()
    if not normalized:
        raise ValueError("A URL is required")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Use a full http:// or https:// URL")
    return normalized


def _fetch_remote_asset(url: str) -> RemoteAssetRecord:
    resource = fetch_remote_resource(
        url,
        max_bytes=settings.remote_document_max_bytes,
        timeout_seconds=settings.metadata_request_timeout_seconds,
        user_agent="OpenChoiceReader/0.1 (+acquisition)",
    )
    filename = _filename_from_content_disposition(resource.headers.get("content-disposition"))
    if filename is None:
        filename = _filename_from_url(resource.final_url)
    return RemoteAssetRecord(
        requested_url=url,
        final_url=resource.final_url,
        content_type=resource.content_type,
        filename=filename,
        body=resource.body,
    )


def _extract_article_snapshot(html: str, url: str) -> ArticleSnapshotRecord:
    try:
        from trafilatura import extract
    except ImportError as error:  # pragma: no cover - depends on the optional article-import runtime
        raise ValueError("Article import runtime is not installed on this host") from error

    cleaned_body = extract(
        html,
        url=url,
        output_format="html",
        favor_recall=True,
        include_comments=False,
    )
    if not cleaned_body:
        raise ValueError("No readable article body could be extracted from that page")

    metadata_payload = extract(
        html,
        url=url,
        output_format="json",
        with_metadata=True,
        favor_recall=True,
        include_comments=False,
    )
    metadata: dict[str, object] = {}
    if metadata_payload:
        try:
            metadata = json.loads(metadata_payload)
        except json.JSONDecodeError:
            metadata = {}

    title = _safe_text(metadata.get("title"))
    author = _safe_text(metadata.get("author"))
    summary = _safe_text(metadata.get("text"))
    normalized_html = _wrap_article_html(cleaned_body=cleaned_body, title=title)
    if summary is None:
        from app.parsers.html import parse_html_document

        parsed = parse_html_document(normalized_html.encode("utf-8"))
        summary = parsed.description
        title = title or parsed.title
        author = author or parsed.author

    return ArticleSnapshotRecord(
        title=title,
        author=author,
        summary=summary[:240] if summary else None,
        cleaned_html=normalized_html,
    )


def _wrap_article_html(*, cleaned_body: str, title: str | None) -> str:
    if "<html" in cleaned_body.lower():
        return cleaned_body

    safe_title = escape(title or "Imported article")
    return (
        "<!DOCTYPE html>"
        "<html><head><meta charset=\"utf-8\" />"
        f"<title>{safe_title}</title>"
        "</head><body>"
        f"{cleaned_body}"
        "</body></html>"
    )


def _build_pasted_text_snapshot(
    *,
    title: str,
    body: str,
    author: str | None,
    source_url: str | None,
    source_site_name: str | None,
) -> str:
    parts = [f"# {title}"]
    normalized_author = author.strip() if isinstance(author, str) and author.strip() else None
    if normalized_author:
        parts.append("")
        parts.append(f"Author: {normalized_author}")
    if source_site_name:
        parts.append("")
        parts.append(f"Source site: {source_site_name}")
    if source_url:
        parts.append("")
        parts.append(f"Source URL: {source_url}")
    parts.append("")
    parts.append(body)
    return "\n".join(parts).strip() + "\n"


def _normalized_extension(filename: str) -> str | None:
    suffix = Path(filename).suffix.lower().lstrip(".")
    return suffix or None


def _infer_extension_from_content_type(content_type: str) -> str | None:
    normalized = content_type.lower()
    if "application/epub+zip" in normalized:
        return "epub"
    if "application/pdf" in normalized:
        return "pdf"
    if "text/markdown" in normalized:
        return "md"
    if "text/plain" in normalized:
        return "txt"
    if "text/html" in normalized:
        return "html"
    return None


def _looks_like_html_response(*, content_type: str, body: bytes) -> bool:
    if "html" in content_type.lower():
        return True
    prefix = body[:512].decode("utf-8", errors="ignore").lower()
    return "<html" in prefix or "<!doctype html" in prefix


def _filename_from_content_disposition(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r'filename="?([^";]+)"?', value, re.IGNORECASE)
    if not match:
        return None
    return Path(match.group(1)).name


def _filename_from_url(url: str) -> str | None:
    path = urlparse(url).path.rstrip("/")
    if not path:
        return None
    name = PurePosixPath(path).name
    return name or None


def _site_name_from_url(url: str | None) -> str | None:
    if not url:
        return None
    hostname = urlparse(url).hostname
    if not hostname:
        return None
    return hostname[4:] if hostname.startswith("www.") else hostname


def _fallback_title_from_url(url: str) -> str:
    filename = _filename_from_url(url)
    if filename:
        stem = Path(filename).stem.replace("-", " ").replace("_", " ").strip()
        if stem:
            return stem.title()
    site_name = _site_name_from_url(url)
    return f"Imported article from {site_name or 'the web'}"


def _slugify_filename(value: str) -> str:
    slug = book_metadata.normalize_for_match(value).replace(" ", "-").strip("-")
    return slug[:80] or "imported-item"


def _extension_suffix(extension: str) -> str:
    return f".{extension.lstrip('.')}"
