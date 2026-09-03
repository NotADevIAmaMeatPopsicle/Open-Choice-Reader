from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys


backend_root = Path(__file__).resolve().parents[1]
os.chdir(backend_root)
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.config import settings  # noqa: E402
from app.main import create_storage_roots  # noqa: E402
from app.services.book_metadata import (  # noqa: E402
    ExternalMetadata,
    build_seed_filename,
    build_external_metadata_from_gutendex,
    fetch_binary_asset,
    fetch_gutendex_book,
    fetch_project_gutenberg_download_asset,
    fetch_project_gutenberg_top_books,
    fetch_remote_bytes,
    parse_top_book_label,
    search_gutendex,
    search_open_library,
)
from app.services.documents import import_local_path, init_database  # noqa: E402
from app.services.library_admin import reset_library  # noqa: E402
from app.services.library_view import get_library_document  # noqa: E402


@dataclass(slots=True)
class SeedResult:
    rank: int
    gutenberg_id: int
    label: str
    filename: str | None
    document_id: int | None
    status: str
    detail: str | None


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed Open Choice Reader with top Project Gutenberg books.")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--reset-library", action="store_true")
    parser.add_argument("--manifest-path", type=Path, default=None)
    args = parser.parse_args()

    create_storage_roots()
    init_database()

    if args.reset_library:
        reset_library()

    top_books = fetch_project_gutenberg_top_books(limit=args.limit)
    if len(top_books) < args.limit:
        print(
            f"Expected {args.limit} books from Project Gutenberg, got {len(top_books)}.",
            file=sys.stderr,
        )
        return 1

    settings.seed_download_root.mkdir(parents=True, exist_ok=True)

    results: list[SeedResult] = []
    for top_book in top_books:
        result = seed_single_book(top_book.rank, top_book.gutenberg_id, top_book.label)
        results.append(result)
        detail = f" ({result.detail})" if result.detail else ""
        print(f"[{result.status}] #{result.rank} {result.gutenberg_id} {top_book.label}{detail}")

    success_count = len([result for result in results if result.status == "imported"])
    manifest_path = args.manifest_path or (
        settings.seed_download_root
        / f"gutenberg-top-{args.limit}-{datetime.now(timezone.utc).date().isoformat()}.json"
    )
    manifest_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "project_gutenberg_top_url": settings.project_gutenberg_top_url,
                "limit": args.limit,
                "results": [asdict(result) for result in results],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if success_count < args.limit:
        print(
            f"Imported {success_count} of {args.limit} requested books. See {manifest_path}.",
            file=sys.stderr,
        )
        return 1

    print(f"Imported {success_count} books. Manifest: {manifest_path}")
    return 0


def seed_single_book(rank: int, gutenberg_id: int, label: str) -> SeedResult:
    title, author = parse_top_book_label(label)
    asset = fetch_project_gutenberg_download_asset(gutenberg_id)
    if asset is None:
        return SeedResult(
            rank=rank,
            gutenberg_id=gutenberg_id,
            label=label,
            filename=None,
            document_id=None,
            status="failed",
            detail="No supported download format",
        )

    metadata_hint = build_seed_metadata_hint(gutenberg_id=gutenberg_id, title=title, author=author)
    filename = build_seed_filename(gutenberg_id, title or label, asset.extension)
    destination = settings.seed_download_root / filename
    destination.write_bytes(fetch_remote_bytes(asset.url))

    try:
        document = import_local_path(destination, metadata_hint=metadata_hint)
        library_document = get_library_document(document.id)
        return SeedResult(
            rank=rank,
            gutenberg_id=gutenberg_id,
            label=label,
            filename=filename,
            document_id=document.id,
            status="imported",
            detail=library_document.title if library_document is not None else None,
        )
    except Exception as error:
        destination.unlink(missing_ok=True)
        return SeedResult(
            rank=rank,
            gutenberg_id=gutenberg_id,
            label=label,
            filename=filename,
            document_id=None,
            status="failed",
            detail=str(error),
        )


def build_seed_metadata_hint(*, gutenberg_id: int, title: str, author: str | None) -> ExternalMetadata:
    exact_record = fetch_gutendex_book(gutenberg_id)
    if exact_record is not None:
        exact_metadata = build_external_metadata_from_gutendex(exact_record, exact_match=True)
        exact_metadata.title = title
        exact_metadata.author = author or exact_metadata.author
        return exact_metadata

    search_record = search_gutendex(title=title, author=author)
    if search_record is not None:
        search_metadata = build_external_metadata_from_gutendex(search_record, exact_match=True)
        search_metadata.title = title
        search_metadata.author = author or search_metadata.author
        return search_metadata

    open_library_match = search_open_library(title=title, author=author)
    cover_bytes = None
    cover_extension = None
    metadata_source = "project_gutenberg"
    metadata_source_id = str(gutenberg_id)

    if open_library_match is not None:
        cover_identifier = open_library_match.get("cover_i")
        if cover_identifier is not None:
            cover_url = f"{settings.open_library_cover_base}/{cover_identifier}-L.jpg"
            cover_bytes, cover_extension = fetch_binary_asset(cover_url)
        metadata_source = "openlibrary"
        metadata_source_id = str(open_library_match.get("key") or gutenberg_id)

    return ExternalMetadata(
        title=title,
        author=author,
        cover_bytes=cover_bytes,
        cover_extension=cover_extension,
        metadata_source=metadata_source,
        metadata_source_id=metadata_source_id,
        exact_match=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
