"""Business logic: all DB operations live here, routes stay thin."""
from fastapi import HTTPException, status
from sqlalchemy import select
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
