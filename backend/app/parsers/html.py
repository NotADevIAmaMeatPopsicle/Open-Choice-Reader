from html.parser import HTMLParser
from xml.etree import ElementTree

from app.parsers.base import ParsedDocument, ParsedSection


class _HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._ignored_depth = 0
        self._title_parts: list[str] = []
        self._title_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style"}:
            self._ignored_depth += 1
        elif tag == "title":
            self._title_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._ignored_depth > 0:
            self._ignored_depth -= 1
        elif tag == "title" and self._title_depth > 0:
            self._title_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth > 0:
            return

        stripped = data.strip()
        if not stripped:
            return

        self._parts.append(stripped)
        if self._title_depth > 0:
            self._title_parts.append(stripped)

    def get_text(self) -> str:
        return "\n".join(self._parts).strip()

    def get_title(self) -> str | None:
        title = " ".join(self._title_parts).strip()
        return title or None


def parse_html_document(file_bytes: bytes) -> ParsedDocument:
    content = file_bytes.decode("utf-8-sig", errors="replace")
    extractor = _HtmlTextExtractor()
    extractor.feed(content)

    text = extractor.get_text()
    title = extractor.get_title() or _extract_first_heading(content)
    author = _extract_author(text)
    sections = [ParsedSection(title=title, text=text)] if text else []
    return ParsedDocument(
        sections=sections,
        title=title,
        author=author,
        description=text[:240] if text else None,
    )


def _extract_first_heading(content: str) -> str | None:
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError:
        return None

    for xpath in (
        ".//{http://www.w3.org/1999/xhtml}h1",
        ".//h1",
    ):
        node = root.find(xpath)
        if node is not None and node.text and node.text.strip():
            return node.text.strip()
    return None


def _extract_author(text: str) -> str | None:
    for line in text.splitlines()[:20]:
        normalized = line.strip()
        if normalized.lower().startswith("author:"):
            author = normalized.split(":", 1)[1].strip()
            return author or None
        if normalized.lower().startswith("by "):
            author = normalized[3:].strip()
            return author or None
    return None
