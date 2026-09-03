from dataclasses import dataclass
from hashlib import sha256
import json
from urllib.parse import urlencode

from app.config import settings
from app.services.remote_fetch import fetch_remote_resource


LIBRIVOX_API_BASE = "https://librivox.org/api/feed"


@dataclass(frozen=True, slots=True)
class CloneSampleCandidate:
    id: str
    provider: str
    title: str
    speaker: str | None
    audio_url: str
    transcript: str | None
    transcript_source_url: str
    source_url: str
    license_label: str
    provenance_note: str
    is_importable: bool


def search_clone_sample_candidates(query: str, *, limit: int = 10) -> list[CloneSampleCandidate]:
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    normalized_limit = max(1, min(limit, 20))
    books_payload = _get_json(
        f"{LIBRIVOX_API_BASE}/audiobooks",
        {"format": "json", "extended": "1", "search": cleaned_query, "limit": normalized_limit},
    )
    books = books_payload.get("books", []) if isinstance(books_payload, dict) else []

    candidates: list[CloneSampleCandidate] = []
    for book in books:
        if len(candidates) >= normalized_limit:
            break
        if not isinstance(book, dict):
            continue

        book_id = str(book.get("id") or "").strip()
        title = str(book.get("title") or "").strip()
        text_source = str(book.get("url_text_source") or "").strip()
        source_url = str(book.get("url_librivox") or "").strip()
        if not book_id or not title or not text_source:
            continue

        sections_payload = _get_json(
            f"{LIBRIVOX_API_BASE}/sections",
            {"format": "json", "extended": "1", "project_id": book_id},
        )
        sections = sections_payload.get("sections", []) if isinstance(sections_payload, dict) else []
        for section in sections:
            if len(candidates) >= normalized_limit:
                break
            if not isinstance(section, dict):
                continue

            audio_url = str(section.get("listen_url") or "").strip()
            section_title = str(section.get("title") or "").strip() or "Sample"
            if not audio_url:
                continue

            candidate_id = sha256(
                f"librivox:{book_id}:{section.get('id')}:{audio_url}".encode("utf-8")
            ).hexdigest()[:16]
            candidates.append(
                CloneSampleCandidate(
                    id=candidate_id,
                    provider="librivox",
                    title=f"{title} - {section_title}",
                    speaker=_format_authors(book.get("authors")),
                    audio_url=audio_url,
                    transcript=None,
                    transcript_source_url=text_source,
                    source_url=source_url or audio_url,
                    license_label="Public domain or LibriVox-provided public-domain recording",
                    provenance_note=(
                        "Candidate discovered through the LibriVox API. Operator must review transcript text "
                        "before importing."
                    ),
                    is_importable=True,
                )
            )

    return candidates


def _format_authors(value) -> str | None:
    if not isinstance(value, list) or not value:
        return None

    names: list[str] = []
    for author in value:
        if not isinstance(author, dict):
            continue
        name = " ".join(
            part
            for part in (
                str(author.get("first_name") or "").strip(),
                str(author.get("last_name") or "").strip(),
            )
            if part
        )
        if name:
            names.append(name)

    return ", ".join(names) or None


def _get_json(url: str, params: dict[str, object]):
    resource = fetch_remote_resource(
        f"{url}?{urlencode(params)}",
        max_bytes=settings.remote_metadata_max_bytes,
        timeout_seconds=settings.metadata_request_timeout_seconds,
        user_agent="OpenChoiceReader/0.1 (+sample-discovery)",
    )
    return json.loads(resource.body)
