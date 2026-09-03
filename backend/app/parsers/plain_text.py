import re

from app.parsers.base import ParsedDocument, ParsedSection


HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(?P<title>.+)$")


def parse_plain_text(content: str, file_format: str) -> list[ParsedSection]:
    return parse_plain_text_document(content, file_format).sections


def parse_plain_text_document(content: str, file_format: str) -> ParsedDocument:
    normalized_format = file_format.lower()
    if normalized_format in {"md", "markdown"}:
        sections = _parse_markdown(content)
        return ParsedDocument(
            sections=sections,
            title=sections[0].title if sections and sections[0].title else None,
            author=_extract_author_from_text(sections[0].text if sections else ""),
        )

    sections = _build_sections([(None, content)])
    return ParsedDocument(
        sections=sections,
        author=_extract_author_from_text(sections[0].text if sections else ""),
    )


def _parse_markdown(content: str) -> list[ParsedSection]:
    sections: list[tuple[str | None, list[str]]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in content.splitlines():
        heading_match = HEADING_PATTERN.match(line.strip())
        if heading_match:
            if current_title is not None or any(part.strip() for part in current_lines):
                sections.append((current_title, current_lines))
            current_title = heading_match.group("title").strip()
            current_lines = []
            continue

        current_lines.append(line)

    if current_title is not None or any(part.strip() for part in current_lines):
        sections.append((current_title, current_lines))

    return _build_sections(sections)


def _build_sections(raw_sections: list[tuple[str | None, str | list[str]]]) -> list[ParsedSection]:
    sections: list[ParsedSection] = []
    for title, body in raw_sections:
        text = "\n".join(body) if isinstance(body, list) else body
        normalized_text = text.strip()
        if not normalized_text:
            continue
        sections.append(ParsedSection(title=title, text=normalized_text))
    return sections


def _extract_author_from_text(text: str) -> str | None:
    for line in text.splitlines()[:3]:
        normalized_line = line.strip()
        if normalized_line.lower().startswith("by "):
            author = normalized_line[3:].strip()
            return author or None
    return None
