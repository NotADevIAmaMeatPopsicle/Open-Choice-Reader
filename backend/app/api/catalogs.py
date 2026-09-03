from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import CurrentUser, get_current_user
from app.schemas.catalog import (
    CatalogImportRequest,
    CatalogResultRead,
    CatalogSourceRead,
    TextImportRequest,
    UrlImportRequest,
)
import app.services.catalogs as catalogs_service
from app.schemas.document import DocumentRead
from app.services.library_view import get_library_document


router = APIRouter(prefix="/api/catalogs", tags=["catalogs"])


@router.get("/sources", response_model=list[CatalogSourceRead])
def list_catalog_sources_route() -> list[CatalogSourceRead]:
    return [CatalogSourceRead.model_validate(source) for source in catalogs_service.list_catalog_sources()]


@router.get("/gutenberg/top", response_model=list[CatalogResultRead])
def browse_gutenberg_route(
    limit: int = 12,
    current_user: CurrentUser = Depends(get_current_user),
) -> list[CatalogResultRead]:
    del current_user
    return [CatalogResultRead.model_validate(result) for result in catalogs_service.browse_gutenberg_catalog(limit=limit)]


@router.get("/gutenberg/search", response_model=list[CatalogResultRead])
def search_gutenberg_route(
    q: str,
    limit: int = 12,
    current_user: CurrentUser = Depends(get_current_user),
) -> list[CatalogResultRead]:
    del current_user
    return [CatalogResultRead.model_validate(result) for result in catalogs_service.search_gutenberg_catalog(q, limit=limit)]


@router.get("/standard-ebooks/browse", response_model=list[CatalogResultRead])
def browse_standard_ebooks_route(
    limit: int = 12,
    sort: str = "new",
    current_user: CurrentUser = Depends(get_current_user),
) -> list[CatalogResultRead]:
    del current_user
    return [
        CatalogResultRead.model_validate(result)
        for result in catalogs_service.browse_standard_ebooks_catalog(limit=limit, sort=sort)
    ]


@router.get("/standard-ebooks/search", response_model=list[CatalogResultRead])
def search_standard_ebooks_route(
    q: str,
    limit: int = 12,
    current_user: CurrentUser = Depends(get_current_user),
) -> list[CatalogResultRead]:
    del current_user
    return [
        CatalogResultRead.model_validate(result)
        for result in catalogs_service.search_standard_ebooks_catalog(q, limit=limit)
    ]


@router.get("/open-library/search", response_model=list[CatalogResultRead])
def search_open_library_route(
    q: str,
    limit: int = 12,
    current_user: CurrentUser = Depends(get_current_user),
) -> list[CatalogResultRead]:
    del current_user
    return [CatalogResultRead.model_validate(result) for result in catalogs_service.search_open_library_catalog(q, limit=limit)]


@router.post("/import", response_model=DocumentRead, status_code=201)
def import_catalog_item_route(
    payload: CatalogImportRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentRead:
    try:
        document = catalogs_service.import_catalog_item(
            source=payload.source,
            catalog_id=payload.catalog_id,
            owner_user_id=current_user.id,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    library_document = get_library_document(document.id, owner_user_id=current_user.id)
    if library_document is None:
        raise HTTPException(status_code=404, detail=f"Document {document.id} was not found after import")
    return DocumentRead.model_validate(library_document)


@router.post("/import-url", response_model=DocumentRead, status_code=201)
def import_catalog_url_route(
    payload: UrlImportRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentRead:
    try:
        document = catalogs_service.import_url_item(payload.url, owner_user_id=current_user.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    library_document = get_library_document(document.id, owner_user_id=current_user.id)
    if library_document is None:
        raise HTTPException(status_code=404, detail=f"Document {document.id} was not found after import")
    return DocumentRead.model_validate(library_document)


@router.post("/import-text", response_model=DocumentRead, status_code=201)
def import_catalog_text_route(
    payload: TextImportRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentRead:
    try:
        document = catalogs_service.import_pasted_text_item(
            title=payload.title,
            body=payload.body,
            author=payload.author,
            source_url=payload.source_url,
            owner_user_id=current_user.id,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    library_document = get_library_document(document.id, owner_user_id=current_user.id)
    if library_document is None:
        raise HTTPException(status_code=404, detail=f"Document {document.id} was not found after import")
    return DocumentRead.model_validate(library_document)
