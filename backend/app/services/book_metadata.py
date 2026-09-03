from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
import json
import re
import unicodedata
from urllib.parse import urlencode, urljoin

from app.config import settings
from app.parsers.base import ParsedDocument
from app.services.remote_fetch import fetch_remote_resource


GUTENBERG_ID_PATTERN = re.compile(r"(?:^|[^0-9])(?:pg|gutenberg[-_])?(\d{1,6})(?:[-_](?:images|noimages|0))?(?=\.|[^0-9]|$)", re.IGNORECASE)
TOP_ENTRY_PATTERN = re.compile(r"<li>\s*<a href=\"/ebooks/(?P<book_id>\d+)\">(?P<label>[^<]+)</a>", re.IGNORECASE)
DOWNLOAD_LINK_PATTERN = re.compile(r"href=\"(?P<href>[^\"]+)\"[^>]*type=\"(?P<media_type>[^\"]+)\"", re.IGNORECASE)


@dataclass(slots=True)
class ExternalMetadata:
    title: str | None = None
    author: str | None = None
    description: str | None = None
    cover_bytes: bytes | None = None
    cover_extension: str | None = None
    metadata_source: str | None = None
    metadata_source_id: str | None = None
    exact_match: bool = False


@dataclass(slots=True)
class MetadataResolution:
    parsed_document: ParsedDocument
    metadata_source: str | None = None
    metadata_source_id: str | None = None


@dataclass(slots=True)
class GutenbergTopBook:
    rank: int
    gutenberg_id: int
    label: str


@dataclass(slots=True)
class DownloadAsset:
    url: str
    media_type: str
    extension: str


def enrich_parsed_document(
    parsed_document: ParsedDocument,
    *,
    filename: Path,
    origin_path: Path | None = None,
    metadata_hint: ExternalMetadata | None = None,
) -> MetadataResolution:
    if metadata_hint is not None:
        return apply_external_metadata(parsed_document, metadata_hint)

    if not settings.metadata_enrichment_enabled:
        return MetadataResolution(parsed_document=parsed_document)

    external_metadata = resolve_external_metadata(
        title=parsed_document.title or filename.stem,
        author=parsed_document.author,
        filename=filename,
        origin_path=origin_path,
    )
    if external_metadata is None:
        return MetadataResolution(parsed_document=parsed_document)

    return apply_external_metadata(parsed_document, external_metadata)


def apply_external_metadata(
    parsed_document: ParsedDocument,
    external_metadata: ExternalMetadata,
) -> MetadataResolution:
    enriched_document = ParsedDocument(
        sections=parsed_document.sections,
        title=parsed_document.title,
        author=parsed_document.author,
        description=parsed_document.description,
        cover_bytes=parsed_document.cover_bytes,
        cover_extension=parsed_document.cover_extension,
    )

    if external_metadata.title and (not parsed_document.title or external_metadata.exact_match):
        enriched_document.title = external_metadata.title
    if external_metadata.author and (not parsed_document.author or external_metadata.exact_match):
        enriched_document.author = external_metadata.author
    if external_metadata.description and (not parsed_document.description or external_metadata.exact_match):
        enriched_document.description = external_metadata.description
    if external_metadata.cover_bytes and (
        parsed_document.cover_bytes is None or external_metadata.exact_match
    ):
        enriched_document.cover_bytes = external_metadata.cover_bytes
        enriched_document.cover_extension = external_metadata.cover_extension

    return MetadataResolution(
        parsed_document=enriched_document,
        metadata_source=external_metadata.metadata_source,
        metadata_source_id=external_metadata.metadata_source_id,
    )


def resolve_external_metadata(
    *,
    title: str | None,
    author: str | None,
    filename: Path,
    origin_path: Path | None,
) -> ExternalMetadata | None:
    gutenberg_id = detect_gutenberg_id(filename=filename, origin_path=origin_path, title=title)
    if gutenberg_id is not None:
        record = fetch_gutendex_book(gutenberg_id)
        if record is not None:
            return build_external_metadata_from_gutendex(record, exact_match=True)

    if not title:
        return None

    open_library_match = search_open_library(title=title, author=author)
    if open_library_match is not None:
        gutenberg_ids = open_library_match.get("id_project_gutenberg") or []
        if gutenberg_ids:
            try:
                gutendex_id = int(str(gutenberg_ids[0]))
            except (TypeError, ValueError):
                gutendex_id = None
            if gutendex_id is not None:
                record = fetch_gutendex_book(gutendex_id)
                if record is not None:
                    return build_external_metadata_from_gutendex(record, exact_match=True)

        cover_bytes = None
        cover_extension = None
        cover_identifier = open_library_match.get("cover_i")
        if cover_identifier is not None:
            cover_url = f"{settings.open_library_cover_base}/{cover_identifier}-L.jpg"
            cover_bytes, cover_extension = fetch_binary_asset(cover_url)

        open_library_title = _safe_strip(open_library_match.get("title"))
        open_library_author = _safe_strip((open_library_match.get("author_name") or [None])[0])
        return ExternalMetadata(
            title=open_library_title,
            author=open_library_author,
            cover_bytes=cover_bytes,
            cover_extension=cover_extension,
            metadata_source="openlibrary",
            metadata_source_id=str(open_library_match.get("key") or open_library_match.get("cover_i") or ""),
            exact_match=False,
        )

    gutendex_match = search_gutendex(title=title, author=author)
    if gutendex_match is not None:
        return build_external_metadata_from_gutendex(gutendex_match, exact_match=False)

    return None


def detect_gutenberg_id(*, filename: Path, origin_path: Path | None, title: str | None) -> int | None:
    for candidate in (
        filename.name,
        filename.stem,
        str(origin_path) if origin_path is not None else None,
        title,
    ):
        if not candidate:
            continue
        match = GUTENBERG_ID_PATTERN.search(str(candidate))
        if match is None:
            continue
        try:
            return int(match.group(1))
        except ValueError:
            continue
    return None


def fetch_project_gutenberg_top_books(limit: int = 30) -> list[GutenbergTopBook]:
    try:
        response_text = fetch_text(settings.project_gutenberg_top_url)
    except ValueError:
        return []

    books = parse_project_gutenberg_top_books(response_text)
    return books[:limit]


def fetch_project_gutenberg_download_asset(book_id: int) -> DownloadAsset | None:
    try:
        html = fetch_text(f"https://www.gutenberg.org/ebooks/{book_id}")
    except ValueError:
        return None

    return parse_project_gutenberg_download_asset(html, book_id=book_id)


def parse_project_gutenberg_top_books(html: str) -> list[GutenbergTopBook]:
    if "Top 100 EBooks yesterday" not in html or "Top 100 Authors yesterday" not in html:
        return []
    section = html.split("Top 100 EBooks yesterday", 1)[1].split("Top 100 Authors yesterday", 1)[0]

    books: list[GutenbergTopBook] = []
    for rank, match in enumerate(TOP_ENTRY_PATTERN.finditer(section), start=1):
        label = re.sub(r"\s+", " ", match.group("label")).strip()
        books.append(
            GutenbergTopBook(
                rank=rank,
                gutenberg_id=int(match.group("book_id")),
                label=label,
            )
        )
    return books


def parse_project_gutenberg_download_asset(html: str, *, book_id: int) -> DownloadAsset | None:
    matches = [
        (
            urljoin("https://www.gutenberg.org/", match.group("href")),
            match.group("media_type").strip(),
        )
        for match in DOWNLOAD_LINK_PATTERN.finditer(html)
    ]
    preferences = (
        ("application/epub+zip", ".epub", (".epub3.images", ".epub.images", ".epub.noimages")),
        ("text/html", ".html", (".html", ".htm")),
        ("text/plain; charset=utf-8", ".txt", (".txt.utf-8", ".txt")),
        ("text/plain", ".txt", (".txt",)),
    )

    for media_type, extension, suffix_preferences in preferences:
        candidates = [url for url, candidate_type in matches if candidate_type == media_type]
        if not candidates:
            continue
        for suffix in suffix_preferences:
            for url in candidates:
                if url.endswith(suffix):
                    return DownloadAsset(url=url, media_type=media_type, extension=extension)
        return DownloadAsset(url=candidates[0], media_type=media_type, extension=extension)

    return None


def fetch_gutendex_book(book_id: int) -> dict | None:
    try:
        return fetch_json(f"{settings.gutendex_api_base.rstrip('/')}/{book_id}")
    except ValueError:
        return None


def search_gutendex(*, title: str, author: str | None) -> dict | None:
    query = {"search": title}
    try:
        payload = fetch_json(f"{settings.gutendex_api_base}?{urlencode(query)}")
    except ValueError:
        return None

    results = payload.get("results") or []
    best_match: tuple[float, dict] | None = None
    normalized_title = normalize_for_match(title)
    normalized_author = normalize_for_match(author or "")

    for record in results[:8]:
        candidate_title = normalize_for_match(record.get("title"))
        candidate_author = normalize_for_match(join_author_names(record.get("authors") or []))
        title_score = SequenceMatcher(a=normalized_title, b=candidate_title).ratio()
        author_score = 1.0 if not normalized_author else SequenceMatcher(a=normalized_author, b=candidate_author).ratio()
        score = round((title_score * 0.8) + (author_score * 0.2), 4)
        if score < 0.9:
            continue
        if best_match is None or score > best_match[0]:
            best_match = (score, record)

    return best_match[1] if best_match is not None else None


def search_open_library(*, title: str, author: str | None) -> dict | None:
    query = {"title": title, "limit": 5}
    if author:
        query["author"] = author

    try:
        payload = fetch_json(f"{settings.open_library_search_url}?{urlencode(query)}")
    except ValueError:
        return None

    normalized_title = normalize_for_match(title)
    normalized_author = normalize_for_match(author or "")
    for record in payload.get("docs") or []:
        candidate_title = normalize_for_match(record.get("title"))
        title_score = SequenceMatcher(a=normalized_title, b=candidate_title).ratio()
        if title_score < 0.9:
            continue

        if normalized_author:
            author_names = record.get("author_name") or []
            joined_authors = normalize_for_match(" ".join(str(name) for name in author_names))
            author_score = SequenceMatcher(a=normalized_author, b=joined_authors).ratio()
            if author_score < 0.6:
                continue

        return record
    return None


def build_external_metadata_from_gutendex(record: dict, *, exact_match: bool) -> ExternalMetadata:
    cover_bytes = None
    cover_extension = None
    formats = record.get("formats") or {}
    cover_url = formats.get("image/jpeg") or formats.get("image/png")
    if isinstance(cover_url, str) and cover_url:
        cover_bytes, cover_extension = fetch_binary_asset(cover_url)

    descriptions = record.get("summaries") or []
    description = _safe_strip(descriptions[0]) if descriptions else None
    return ExternalMetadata(
        title=_safe_strip(record.get("title")),
        author=join_author_names(record.get("authors") or []),
        description=description,
        cover_bytes=cover_bytes,
        cover_extension=cover_extension,
        metadata_source="gutendex",
        metadata_source_id=str(record.get("id") or ""),
        exact_match=exact_match,
    )


def select_download_asset(record: dict) -> DownloadAsset | None:
    formats = record.get("formats") or {}
    preferences = (
        ("application/epub+zip", ".epub"),
        ("text/plain; charset=utf-8", ".txt"),
        ("text/plain", ".txt"),
    )

    for media_type, extension in preferences:
        url = formats.get(media_type)
        if isinstance(url, str) and url:
            return DownloadAsset(url=url, media_type=media_type, extension=extension)
    return None


def build_seed_filename(book_id: int, title: str, extension: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalize_for_match(title)).strip("-")
    safe_slug = slug[:64] or f"book-{book_id}"
    return f"gutenberg-{book_id}-{safe_slug}{extension}"


def parse_top_book_label(label: str) -> tuple[str, str | None]:
    without_downloads = re.sub(r"\s*\(\d+\)\s*$", "", label).strip()
    title, separator, author = without_downloads.rpartition(" by ")
    if separator:
        return title.strip(), author.strip() or None
    return without_downloads, None


def fetch_json(url: str) -> dict:
    resource = fetch_remote_resource(
        url,
        max_bytes=settings.remote_metadata_max_bytes,
        timeout_seconds=settings.metadata_request_timeout_seconds,
        user_agent="OpenChoiceReader/0.1 (+metadata-enrichment)",
    )
    payload = json.loads(resource.body)
    if not isinstance(payload, dict):
        raise ValueError("The metadata service returned an unexpected response")
    return payload


def fetch_text(url: str) -> str:
    resource = fetch_remote_resource(
        url,
        max_bytes=settings.remote_metadata_max_bytes,
        timeout_seconds=settings.metadata_request_timeout_seconds,
        user_agent="OpenChoiceReader/0.1 (+metadata-enrichment)",
    )
    return resource.body.decode("utf-8", errors="replace")


def fetch_binary_asset(url: str) -> tuple[bytes | None, str | None]:
    try:
        resource = fetch_remote_resource(
            url,
            max_bytes=settings.remote_image_max_bytes,
            timeout_seconds=settings.metadata_request_timeout_seconds,
            user_agent="OpenChoiceReader/0.1 (+metadata-enrichment)",
        )
        if "png" in resource.content_type.lower():
            return resource.body, ".png"
        return resource.body, ".jpg"
    except ValueError:
        return None, None


def fetch_remote_bytes(url: str) -> bytes:
    return fetch_remote_resource(
        url,
        max_bytes=settings.remote_document_max_bytes,
        timeout_seconds=settings.metadata_request_timeout_seconds,
        user_agent="OpenChoiceReader/0.1 (+acquisition)",
    ).body


def join_author_names(authors: list[dict]) -> str | None:
    names = [_safe_strip(author.get("name")) for author in authors if isinstance(author, dict)]
    filtered_names = [name for name in names if name]
    if not filtered_names:
        return None
    return ", ".join(filtered_names)


def normalize_for_match(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.lower()
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


def _safe_strip(value) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
