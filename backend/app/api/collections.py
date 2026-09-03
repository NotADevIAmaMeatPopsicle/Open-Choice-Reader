from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.dependencies import CurrentUser, get_current_user
from app.schemas.collection import CollectionCreate, CollectionDocumentAdd, CollectionRead
from app.services.collections import (
    add_document_to_collection,
    create_collection,
    list_collections,
    remove_document_from_collection,
)


router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.get("", response_model=list[CollectionRead])
def list_collections_route(current_user: CurrentUser = Depends(get_current_user)) -> list[CollectionRead]:
    return [
        CollectionRead.model_validate(collection)
        for collection in list_collections(owner_user_id=current_user.id)
    ]


@router.post("", response_model=CollectionRead, status_code=201)
def create_collection_route(
    payload: CollectionCreate,
    current_user: CurrentUser = Depends(get_current_user),
) -> CollectionRead:
    try:
        collection = create_collection(
            name=payload.name,
            description=payload.description,
            owner_user_id=current_user.id,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return CollectionRead.model_validate(collection)


@router.post("/{collection_id}/documents", response_model=CollectionRead)
def add_document_to_collection_route(
    collection_id: int,
    payload: CollectionDocumentAdd,
    current_user: CurrentUser = Depends(get_current_user),
) -> CollectionRead:
    try:
        collection = add_document_to_collection(
            collection_id=collection_id,
            document_id=payload.document_id,
            owner_user_id=current_user.id,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return CollectionRead.model_validate(collection)


@router.delete("/{collection_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_document_from_collection_route(
    collection_id: int,
    document_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> Response:
    try:
        remove_document_from_collection(
            collection_id=collection_id,
            document_id=document_id,
            owner_user_id=current_user.id,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
