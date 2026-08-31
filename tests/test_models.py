"""Unit tests for SQLAlchemy models and pydantic schemas."""
import re
from datetime import datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models import Board, Element
from backend.schemas import ElementCreate, ElementType

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


@pytest.fixture()
def db():
    """Isolated in-memory database per test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_board_defaults(db):
    board = Board()
    db.add(board)
    db.commit()
    db.refresh(board)

    assert UUID_RE.match(board.id)
    assert board.name is None
    assert isinstance(board.created_at, datetime)
    assert board.elements == []


def test_board_with_name(db):
    board = Board(name="Rate limiter design")
    db.add(board)
    db.commit()
    db.refresh(board)

    assert board.name == "Rate limiter design"


def test_element_defaults(db):
    board = Board()
    db.add(board)
    db.commit()

    element = Element(
        board_id=board.id,
        type="sticky_note",
        x=120,
        y=80,
        width=160,
        height=160,
        text="API Gateway",
    )
    db.add(element)
    db.commit()
    db.refresh(element)

    assert UUID_RE.match(element.id)
    assert element.board_id == board.id
    assert element.type == "sticky_note"
    assert element.text == "API Gateway"
    assert isinstance(element.created_at, datetime)


def test_element_text_is_nullable(db):
    board = Board()
    db.add(board)
    db.commit()

    element = Element(board_id=board.id, type="rectangle", x=0, y=0, width=180, height=110)
    db.add(element)
    db.commit()
    db.refresh(element)

    assert element.text is None


def test_relationship_back_populates(db):
    board = Board()
    db.add(board)
    db.commit()

    element = Element(type="circle", x=0, y=0, width=130, height=130)
    board.elements.append(element)
    db.commit()

    assert element.board is board
    assert len(board.elements) == 1


def test_delete_board_cascades_to_elements(db):
    board = Board()
    db.add(board)
    db.commit()
    board.elements.append(Element(type="circle", x=0, y=0, width=130, height=130))
    db.commit()

    db.delete(board)
    db.commit()

    assert db.scalars(select(Element)).all() == []


# ---- schema constraints (mirror openapi.yaml) ----

def test_element_type_enum_values():
    assert [t.value for t in ElementType] == ["sticky_note", "rectangle", "circle"]


def test_element_create_rejects_unknown_type():
    with pytest.raises(ValidationError):
        ElementCreate.model_validate({"type": "triangle", "x": 0, "y": 0, "width": 10, "height": 10})


def test_element_create_rejects_non_positive_size():
    with pytest.raises(ValidationError):
        ElementCreate(type=ElementType.rectangle, x=0, y=0, width=0, height=10)


def test_element_create_accepts_missing_text():
    el = ElementCreate(type=ElementType.circle, x=0, y=0, width=10, height=10)
    assert el.text is None
