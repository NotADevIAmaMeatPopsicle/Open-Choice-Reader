from io import BytesIO

from pypdf import PdfReader

from app.config import settings
from app.parsers.base import ParsedDocument, ParsedSection


def parse_pdf_document(file_bytes: bytes) -> ParsedDocument:
    reader = PdfReader(BytesIO(file_bytes))
    if len(reader.pages) > settings.pdf_max_pages:
        raise ValueError(f"PDF exceeds the {settings.pdf_max_pages}-page limit")
    sections: list[ParsedSection] = []
    extracted_characters = 0

    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        extracted_characters += len(text)
        if extracted_characters > settings.pdf_max_extracted_chars:
            raise ValueError(
                f"PDF extracted text exceeds the {settings.pdf_max_extracted_chars}-character limit"
            )
        sections.append(ParsedSection(title=f"Page {page_number}", text=text))

    metadata = reader.metadata or {}
    title = getattr(metadata, "title", None) or metadata.get("/Title")
    author = getattr(metadata, "author", None) or metadata.get("/Author")

    return ParsedDocument(
        sections=sections,
        title=title.strip() if isinstance(title, str) and title.strip() else None,
        author=author.strip() if isinstance(author, str) and author.strip() else None,
    )


def parse_pdf_bytes(file_bytes: bytes) -> list[ParsedSection]:
    return parse_pdf_document(file_bytes).sections
