"""Pydantic API contracts — mirrors the schemas in openapi.yaml."""
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ElementType(StrEnum):
    sticky_note = "sticky_note"
    rectangle = "rectangle"
    circle = "circle"


def to_utc_z(dt: datetime) -> str:
    """Serialize an aware datetime as RFC3339 UTC with 'Z' (matches openapi.yaml examples)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class BoardCreate(BaseModel):
    name: str | None = Field(default=None, max_length=120)


class ElementCreate(BaseModel):
    type: ElementType
    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    text: str | None = Field(default=None, max_length=500)


class ElementUpdate(BaseModel):
    """Partial update — only fields present in the request are applied.

    `model_dump(exclude_unset=True)` in the service distinguishes an omitted
    field from an explicit `null` (used to clear `text`).
    """

    x: float | None = None
    y: float | None = None
    text: str | None = Field(default=None, max_length=500)


class ElementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    board_id: str
    type: ElementType
    x: float
    y: float
    width: float
    height: float
    text: str | None
    created_at: datetime

    @field_serializer("created_at")
    def _ser_created_at(self, dt: datetime) -> str:
        return to_utc_z(dt)


class BoardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str | None
    created_at: datetime
    elements: list[ElementOut]

    @field_serializer("created_at")
    def _ser_created_at(self, dt: datetime) -> str:
        return to_utc_z(dt)


class HealthOut(BaseModel):
    """Matches the Health schema in openapi.yaml."""

    status: str
    database: str
