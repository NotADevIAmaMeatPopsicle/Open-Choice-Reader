from html.parser import HTMLParser
from io import BytesIO
from pathlib import PurePosixPath
from urllib.parse import unquote
from xml.etree import ElementTree
from zipfile import ZipFile

from app.config import settings
from app.parsers.base import ParsedDocument, ParsedSection


CONTAINER_NAMESPACE = {"container": "urn:oasis:names:tc:opendocument:xmlns:container"}
OPF_NAMESPACE = {"opf": "http://www.idpf.org/2007/opf"}
DC_NAMESPACE = {"dc": "http://purl.org/dc/elements/1.1/"}


class _BoundedArchiveReader:
    def __init__(self, archive: ZipFile) -> None:
        self._archive = archive
        self._remaining_bytes = settings.epub_max_uncompressed_bytes
        self._validate_archive_metadata()

    def _validate_archive_metadata(self) -> None:
        members = self._archive.infolist()
        if len(members) > settings.epub_max_entries:
            raise ValueError(
                f"EPUB contains more than {settings.epub_max_entries} archive entries"
            )

        total_uncompressed_bytes = 0
        for member in members:
            if member.flag_bits & 0x1:
                raise ValueError("Encrypted EPUB archive entries are not supported")
            if member.is_dir():
                continue
            if member.file_size > settings.epub_max_member_bytes:
                raise ValueError(
                    f"EPUB archive entry exceeds the {settings.epub_max_member_bytes}-byte limit"
                )
            compression_ratio = member.file_size / max(member.compress_size, 1)
            if compression_ratio > settings.epub_max_compression_ratio:
                raise ValueError(
                    "EPUB archive entry exceeds the allowed compression ratio"
                )
            total_uncompressed_bytes += member.file_size
            if total_uncompressed_bytes > settings.epub_max_uncompressed_bytes:
                raise ValueError(
                    "EPUB archive exceeds the configured uncompressed-size limit"
                )

    def read(self, member_name: str) -> bytes:
        member = self._archive.getinfo(member_name)
        if member.file_size > self._remaining_bytes:
            raise ValueError("EPUB parsing exceeded the configured uncompressed-size limit")

        with self._archive.open(member) as source:
            payload = source.read(settings.epub_max_member_bytes + 1)
        if len(payload) > settings.epub_max_member_bytes:
            raise ValueError(
                f"EPUB archive entry exceeds the {settings.epub_max_member_bytes}-byte limit"
            )

        self._remaining_bytes -= len(payload)
        return payload


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self._parts.append(stripped)

    def get_text(self) -> str:
        return " ".join(self._parts).strip()


def parse_epub_document(file_bytes: bytes) -> ParsedDocument:
    with ZipFile(BytesIO(file_bytes)) as archive:
        reader = _BoundedArchiveReader(archive)
        container_xml = reader.read("META-INF/container.xml")
        container_root = ElementTree.fromstring(container_xml)
        rootfile = container_root.find(
            "container:rootfiles/container:rootfile", CONTAINER_NAMESPACE
        )
        if rootfile is None:
            return ParsedDocument(sections=[])

        package_path = PurePosixPath(rootfile.attrib["full-path"])
        package_root = ElementTree.fromstring(reader.read(str(package_path)))
        manifest = {
            item.attrib["id"]: item
            for item in package_root.findall("opf:manifest/opf:item", OPF_NAMESPACE)
            if "id" in item.attrib and "href" in item.attrib
        }

        sections: list[ParsedSection] = []
        for position, itemref in enumerate(
            package_root.findall("opf:spine/opf:itemref", OPF_NAMESPACE),
            start=1,
        ):
            manifest_item = manifest.get(itemref.attrib.get("idref", ""))
            if manifest_item is None:
                continue

            section_path = _resolve_archive_path(package_path, manifest_item.attrib["href"])
            content = reader.read(str(section_path)).decode("utf-8")
            text = _extract_xhtml_text(content)
            if not text:
                continue

            title = _extract_xhtml_title(content)
            sections.append(ParsedSection(title=title or f"Section {position}", text=text))

        cover_bytes, cover_extension = _extract_cover_asset(
            archive=archive,
            reader=reader,
            package_path=package_path,
            package_root=package_root,
            manifest=manifest,
        )

        return ParsedDocument(
            title=_extract_package_text(package_root, "dc:title"),
            author=_extract_package_text(package_root, "dc:creator"),
            description=_extract_package_text(package_root, "dc:description"),
            cover_bytes=cover_bytes,
            cover_extension=cover_extension,
            sections=sections,
        )


def parse_epub_bytes(file_bytes: bytes) -> list[ParsedSection]:
    return parse_epub_document(file_bytes).sections


def _extract_xhtml_title(content: str) -> str | None:
    root = ElementTree.fromstring(content)

    for xpath in (
        ".//{http://www.w3.org/1999/xhtml}h1",
        ".//{http://www.w3.org/1999/xhtml}title",
    ):
        node = root.find(xpath)
        if node is not None and node.text and node.text.strip():
            return node.text.strip()
    return None


def _extract_xhtml_text(content: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(content)
    return extractor.get_text()


def _resolve_archive_path(package_path: PurePosixPath, href: str) -> PurePosixPath:
    decoded_href = unquote(href)
    joined_path = package_path.parent.joinpath(PurePosixPath(decoded_href))
    normalized_parts: list[str] = []

    for part in joined_path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if normalized_parts:
                normalized_parts.pop()
            continue
        normalized_parts.append(part)

    return PurePosixPath(*normalized_parts)


def _extract_package_text(package_root: ElementTree.Element, tag: str) -> str | None:
    node = package_root.find(f"opf:metadata/{tag}", {**OPF_NAMESPACE, **DC_NAMESPACE})
    if node is None or node.text is None:
        return None

    text = node.text.strip()
    return text or None


def _extract_cover_asset(
    *,
    archive: ZipFile,
    reader: _BoundedArchiveReader,
    package_path: PurePosixPath,
    package_root: ElementTree.Element,
    manifest: dict[str, ElementTree.Element],
) -> tuple[bytes | None, str | None]:
    cover_item = next(
        (
            item
            for item in manifest.values()
            if "cover-image" in item.attrib.get("properties", "").split()
        ),
        None,
    )
    if cover_item is None:
        cover_meta = package_root.find("opf:metadata/opf:meta[@name='cover']", OPF_NAMESPACE)
        if cover_meta is not None:
            cover_item = manifest.get(cover_meta.attrib.get("content", ""))

    if cover_item is None:
        return None, None

    cover_href = cover_item.attrib.get("href")
    if not cover_href:
        return None, None

    cover_path = _resolve_archive_path(package_path, cover_href)
    cover_extension = PurePosixPath(cover_href).suffix.lower() or ".bin"
    return reader.read(str(cover_path)), cover_extension
