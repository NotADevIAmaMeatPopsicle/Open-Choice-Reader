from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse

from app.api.dependencies import CurrentUser, get_current_user
from app.schemas.document import (
    BookmarkPreferenceUpdate,
    DocumentDetailRead,
    DocumentRead,
    DocumentSummaryRead,
    InboxCandidate,
    InboxImportRequest,
)
from app.services.documents import (
    delete_document,
    import_document,
    import_inbox_candidate,
    reimport_document,
)
from app.services.library_view import (
    get_cover_path,
    get_library_document,
    get_library_document_detail,
    get_library_summary,
    list_library_documents,
    reset_document_bookmark,
    set_document_bookmark_enabled,
    set_document_finished,
)
from app.services.library_scan import list_inbox_candidates


router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/import", response_model=DocumentRead, status_code=201)
def import_document_route(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentRead:
    try:
        document = import_document(file, owner_user_id=current_user.id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    library_document = get_library_document(document.id, owner_user_id=current_user.id)
    if library_document is None:
        raise HTTPException(status_code=404, detail=f"Document {document.id} was not found after import")
    return DocumentRead.model_validate(library_document)


@router.post("/import-inbox", response_model=DocumentRead, status_code=201)
def import_inbox_document_route(
    payload: InboxImportRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentRead:
    try:
        document = import_inbox_candidate(payload.path, owner_user_id=current_user.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    library_document = get_library_document(document.id, owner_user_id=current_user.id)
    if library_document is None:
        raise HTTPException(status_code=404, detail=f"Document {document.id} was not found after import")
    return DocumentRead.model_validate(library_document)


@router.get("/inbox", response_model=list[InboxCandidate])
def list_inbox_route(current_user: CurrentUser = Depends(get_current_user)) -> list[InboxCandidate]:
    return list_inbox_candidates(owner_user_id=current_user.id)


@router.get("/summary", response_model=DocumentSummaryRead)
def get_library_summary_route(
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentSummaryRead:
    return DocumentSummaryRead.model_validate(get_library_summary(owner_user_id=current_user.id))


@router.get("/{document_id}", response_model=DocumentDetailRead)
def get_document_route(
    document_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentDetailRead:
    document = get_library_document_detail(document_id, owner_user_id=current_user.id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} was not found")

    return DocumentDetailRead.model_validate(document)


@router.delete("/{document_id}", status_code=204)
def delete_document_route(
    document_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> Response:
    try:
        delete_document(document_id, owner_user_id=current_user.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return Response(status_code=204)


@router.post("/{document_id}/reimport", response_model=DocumentRead)
def reimport_document_route(
    document_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentRead:
    try:
        document = reimport_document(document_id, owner_user_id=current_user.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    library_document = get_library_document(document.id, owner_user_id=current_user.id)
    if library_document is None:
        raise HTTPException(status_code=404, detail=f"Document {document.id} was not found after re-import")
    return DocumentRead.model_validate(library_document)


@router.post("/{document_id}/bookmark/reset", response_model=DocumentRead)
def reset_document_bookmark_route(
    document_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentRead:
    try:
        document = reset_document_bookmark(document_id=document_id, owner_user_id=current_user.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return DocumentRead.model_validate(document)


@router.patch("/{document_id}/bookmark", response_model=DocumentRead)
def update_document_bookmark_route(
    document_id: int,
    payload: BookmarkPreferenceUpdate,
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentRead:
    try:
        document = set_document_bookmark_enabled(
            document_id=document_id,
            enabled=payload.enabled,
            owner_user_id=current_user.id,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return DocumentRead.model_validate(document)


@router.post("/{document_id}/finished", response_model=DocumentRead)
def mark_document_finished_route(
    document_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentRead:
    try:
        document = set_document_finished(document_id=document_id, is_finished=True, owner_user_id=current_user.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return DocumentRead.model_validate(document)


@router.delete("/{document_id}/finished", response_model=DocumentRead)
def clear_document_finished_route(
    document_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentRead:
    try:
        document = set_document_finished(document_id=document_id, is_finished=False, owner_user_id=current_user.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return DocumentRead.model_validate(document)


@router.get("/{document_id}/cover")
def get_document_cover_route(
    document_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> FileResponse:
    try:
        cover_path = get_cover_path(document_id, owner_user_id=current_user.id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    media_type = "image/svg+xml" if cover_path.suffix.lower() == ".svg" else None
    return FileResponse(cover_path, media_type=media_type)


@router.get("", response_model=list[DocumentRead])
def list_documents_route(current_user: CurrentUser = Depends(get_current_user)) -> list[DocumentRead]:
    return [
        DocumentRead.model_validate(document)
        for document in list_library_documents(owner_user_id=current_user.id)
    ]
