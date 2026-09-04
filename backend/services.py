"""Business logic: all DB operations live here, routes stay thin."""
from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from . import models, schemas


def create_board(db: Session, payload: schemas.BoardCreate | None) -> models.Board:
    board = models.Board(name=payload.name if payload else None)
    db.add(board)
    db.commit()
    db.refresh(board)
    return board


def get_board(db: Session, board_id: str) -> models.Board:
    # eager-load elements so the response can be serialized after the session closes
    board = db.scalars(
        select(models.Board)
        .options(selectinload(models.Board.elements))
        .where(models.Board.id == board_id)
    ).first()
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    return board


def delete_board(db: Session, board_id: str) -> None:
    board = db.get(models.Board, board_id)
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    db.delete(board)
    db.commit()


def add_element(db: Session, board_id: str, payload: schemas.ElementCreate) -> models.Element:
    board = db.get(models.Board, board_id)
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    element = models.Element(
        board_id=board_id,
        type=payload.type.value,
        x=payload.x,
        y=payload.y,
        width=payload.width,
        height=payload.height,
        text=payload.text,
    )
    db.add(element)
    db.commit()
    db.refresh(element)
    return element


def delete_element(db: Session, element_id: str) -> None:
    element = db.get(models.Element, element_id)
    if element is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Element not found")
    db.delete(element)
    db.commit()


def update_element(
    db: Session, element_id: str, payload: schemas.ElementUpdate
) -> models.Element:
    """Apply a partial update: only fields present in the payload change.

    `exclude_unset` keeps an explicit `null` (e.g. `{"text": null}` clears the
    text) distinct from an omitted field (left unchanged).
    """
    element = db.get(models.Element, element_id)
    if element is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Element not found")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(element, field, value)
    db.commit()
    db.refresh(element)
    return element


def health_check(db: Session) -> dict:
    """Service and database health. Raises 503 when the DB is unreachable."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc
    return {"status": "ok", "database": "ok"}
