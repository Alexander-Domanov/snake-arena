"""API routes — exactly the four endpoints from openapi.yaml."""
import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from . import models, schemas, services
from .database import get_db

router = APIRouter()


@router.post(
    "/boards",
    response_model=schemas.BoardOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a board",
)
def create_board(
    payload: schemas.BoardCreate | None = None,
    db: Session = Depends(get_db),
) -> models.Board:
    return services.create_board(db, payload)


@router.get(
    "/boards/{board_id}",
    response_model=schemas.BoardOut,
    summary="Get a board",
)
def get_board(board_id: uuid.UUID, db: Session = Depends(get_db)) -> models.Board:
    return services.get_board(db, str(board_id))


@router.post(
    "/boards/{board_id}/elements",
    response_model=schemas.ElementOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add an element",
)
def add_element(
    board_id: uuid.UUID,
    payload: schemas.ElementCreate,
    db: Session = Depends(get_db),
) -> models.Element:
    return services.add_element(db, str(board_id), payload)


@router.patch(
    "/elements/{element_id}",
    response_model=schemas.ElementOut,
    summary="Update an element",
)
def patch_element(
    element_id: uuid.UUID,
    payload: schemas.ElementUpdate,
    db: Session = Depends(get_db),
) -> models.Element:
    return services.update_element(db, str(element_id), payload)


@router.delete(
    "/elements/{element_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an element",
)
def delete_element(
    element_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Response:
    services.delete_element(db, str(element_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/healthz",
    response_model=schemas.HealthOut,
    summary="Health check",
)
def healthz(db: Session = Depends(get_db)) -> dict:
    return services.health_check(db)
