from html import escape
from pathlib import Path

from app.config import settings


def covers_root(*, destination_root: Path | None = None) -> Path:
    path = destination_root or (settings.storage_root / "covers")
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_cover_asset(
    *,
    document_id: int,
    title: str,
    author: str | None,
    file_format: str,
    cover_bytes: bytes | None,
    cover_extension: str | None,
    destination_root: Path | None = None,
) -> Path:
    root = covers_root(destination_root=destination_root)
    if cover_bytes and cover_extension:
        destination = root / f"document-{document_id}{cover_extension.lower()}"
        destination.write_bytes(cover_bytes)
        return destination

    destination = root / f"document-{document_id}.svg"
    destination.write_text(
        _build_placeholder_svg(title=title, author=author, file_format=file_format),
        encoding="utf-8",
    )
    return destination


def _build_placeholder_svg(*, title: str, author: str | None, file_format: str) -> str:
    accent = _accent_color(title)
    safe_title = escape(title[:42] or "Untitled")
    safe_author = escape((author or file_format.upper())[:42])

    return f"""<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="320" height="480" viewBox="0 0 320 480">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#111827"/>
      <stop offset="100%" stop-color="#020617"/>
    </linearGradient>
  </defs>
  <rect width="320" height="480" fill="url(#bg)"/>
  <rect x="22" y="22" width="276" height="436" rx="24" fill="{accent}" opacity="0.18"/>
  <rect x="38" y="38" width="244" height="404" rx="20" fill="none" stroke="{accent}" stroke-width="2"/>
  <text x="42" y="88" fill="#f8fafc" font-family="Georgia" font-size="30" font-weight="700">{safe_title}</text>
  <text x="42" y="130" fill="#cbd5e1" font-family="Georgia" font-size="18">{safe_author}</text>
  <text x="42" y="430" fill="{accent}" font-family="Arial" font-size="16" letter-spacing="3">{escape(file_format.upper())}</text>
</svg>
"""


def _accent_color(seed: str) -> str:
    palette = ["#f59e0b", "#38bdf8", "#fb7185", "#34d399", "#f97316", "#a78bfa"]
    if not seed:
        return palette[0]
    return palette[sum(ord(character) for character in seed) % len(palette)]
