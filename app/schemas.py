from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError


class HabitBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise PydanticCustomError(
                "blank_name", "название привычки не должно быть пустым"
            )
        return normalized

    @field_validator("description", "category")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class HabitCreate(HabitBase):
    pass


class HabitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    category: str | None
    is_active: bool
    created_at: datetime


class HabitArchiveResponse(BaseModel):
    id: int
    is_active: bool


class CompletionCreate(BaseModel):
    completed_on: date


class CompletionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    habit_id: int
    completed_on: date
    created_at: datetime


class HabitStats(BaseModel):
    habit_id: int
    name: str
    is_active: bool
    total_completions: int
    current_streak: int
    best_streak: int
    last_completed_on: date | None


class HabitListItem(BaseModel):
    id: int
    name: str
    is_active: bool
    current_streak: int
    best_streak: int
    total_completions: int


class HabitAggregateStats(BaseModel):
    total_habits: int
    active_habits: int
    archived_habits: int
    total_completions: int
    max_best_streak: int
