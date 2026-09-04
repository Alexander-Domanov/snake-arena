"""API routes — exactly the six data endpoints from openapi.yaml (plus /healthz)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from . import models, schemas, services, telemetry
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
    board = services.create_board(db, payload)
    telemetry.boards_created.add(1)
    telemetry.record_board_activity(str(board.id))
    return board


@router.get(
    "/boards/{board_id}",
    response_model=schemas.BoardOut,
    summary="Get a board",
)
def get_board(board_id: uuid.UUID, db: Session = Depends(get_db)) -> models.Board:
    board = services.get_board(db, str(board_id))
    telemetry.record_board_activity(str(board.id))
    return board


@router.delete(
    "/boards/{board_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a board",
)
def delete_board(board_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    services.delete_board(db, str(board_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    try:
        element = services.add_element(db, str(board_id), payload)
    except HTTPException as exc:
        # 404 (board missing) is the only business failure today; 422 request
        # validation errors happen before this handler and are not counted.
        reason = (
            "board_not_found"
            if exc.status_code == status.HTTP_404_NOT_FOUND
            else f"http_{exc.status_code}"
        )
        telemetry.element_creation_failures.add(1, {"reason": reason})
        raise
    except Exception:
        telemetry.element_creation_failures.add(1, {"reason": "internal_error"})
        raise
    telemetry.elements_created.add(1, {"type": payload.type.value})
    telemetry.record_board_activity(str(board_id))
    return element


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
