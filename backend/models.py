"""SQLAlchemy ORM models. Shapes match the schemas in openapi.yaml (uuid strings, UTC datetimes)."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    elements: Mapped[list["Element"]] = relationship(
        back_populates="board",
        cascade="all, delete-orphan",
    )


class Element(Base):
    __tablename__ = "elements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    board_id: Mapped[str] = mapped_column(ForeignKey("boards.id"), index=True)
    type: Mapped[str] = mapped_column(String(20))  # one of ElementType values from openapi.yaml
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    width: Mapped[float] = mapped_column(Float)
    height: Mapped[float] = mapped_column(Float)
    text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    board: Mapped["Board"] = relationship(back_populates="elements")
