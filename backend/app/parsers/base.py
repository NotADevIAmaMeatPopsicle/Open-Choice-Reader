from dataclasses import dataclass


@dataclass(slots=True)
class ParsedSection:
    title: str | None
    text: str


@dataclass(slots=True)
class ParsedDocument:
    sections: list[ParsedSection]
    title: str | None = None
    author: str | None = None
    description: str | None = None
    cover_bytes: bytes | None = None
    cover_extension: str | None = None
