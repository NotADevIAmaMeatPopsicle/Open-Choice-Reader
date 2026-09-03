from dataclasses import dataclass

from sqlalchemy import select

from app import db
from app.models.collection import Collection, CollectionDocument
from app.models.document import Document
from app.services.library_view import get_library_document


@dataclass(slots=True)
class CollectionDocumentRecord:
    id: int
    title: str
    author: str | None
    cover_url: str
    progress_percent: float


@dataclass(slots=True)
class CollectionRecord:
    id: int
    name: str
    description: str | None
    document_count: int
    documents: list[CollectionDocumentRecord]


def list_collections(*, owner_user_id: int | None = None) -> list[CollectionRecord]:
    with db.session_scope() as session:
        statement = select(Collection).order_by(Collection.name)
        if owner_user_id is not None:
            statement = statement.where(Collection.owner_user_id == owner_user_id)
        collections = list(session.scalars(statement))
        return [_build_collection_record(collection, owner_user_id=owner_user_id) for collection in collections]


def create_collection(
    *,
    name: str,
    description: str | None,
    owner_user_id: int | None = None,
) -> CollectionRecord:
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Collection name is required")

    with db.session_scope() as session:
        collection = Collection(
            owner_user_id=owner_user_id,
            name=normalized_name,
            description=(description or "").strip() or None,
        )
        session.add(collection)
        session.flush()
        session.refresh(collection)
        return _build_collection_record(collection, owner_user_id=owner_user_id)


def add_document_to_collection(
    *,
    collection_id: int,
    document_id: int,
    owner_user_id: int | None = None,
) -> CollectionRecord:
    with db.session_scope() as session:
        collection = session.get(Collection, collection_id)
        if collection is None or (owner_user_id is not None and collection.owner_user_id != owner_user_id):
            raise LookupError(f"Collection {collection_id} was not found")
        document = session.get(Document, document_id)
        if document is None or (owner_user_id is not None and document.owner_user_id != owner_user_id):
            raise LookupError(f"Document {document_id} was not found")

        existing = session.get(CollectionDocument, {"collection_id": collection_id, "document_id": document_id})
        if existing is None:
            session.add(CollectionDocument(collection_id=collection_id, document_id=document_id))
            session.flush()

        return _build_collection_record(collection, owner_user_id=owner_user_id)


def remove_document_from_collection(
    *,
    collection_id: int,
    document_id: int,
    owner_user_id: int | None = None,
) -> None:
    with db.session_scope() as session:
        collection = session.get(Collection, collection_id)
        if collection is None or (owner_user_id is not None and collection.owner_user_id != owner_user_id):
            raise LookupError(f"Collection {collection_id} was not found")

        membership = session.get(
            CollectionDocument,
            {"collection_id": collection_id, "document_id": document_id},
        )
        if membership is None:
            raise LookupError(
                f"Document {document_id} is not a member of collection {collection_id}"
            )

        session.delete(membership)


def _build_collection_record(collection: Collection, *, owner_user_id: int | None = None) -> CollectionRecord:
    documents: list[CollectionDocumentRecord] = []
    membership_rows = sorted(collection.membership_rows, key=lambda row: row.document_id)
    for membership in membership_rows:
        library_document = get_library_document(membership.document_id, owner_user_id=owner_user_id)
        if library_document is None:
            continue
        documents.append(
            CollectionDocumentRecord(
                id=library_document.id,
                title=library_document.title,
                author=library_document.author,
                cover_url=library_document.cover_url,
                progress_percent=library_document.progress_percent,
            )
        )

    return CollectionRecord(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        document_count=len(documents),
        documents=documents,
    )
