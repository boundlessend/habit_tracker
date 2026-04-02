from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.services import habits as habit_service

router = APIRouter(prefix="/habits", tags=["habits"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "", response_model=schemas.HabitRead, status_code=status.HTTP_201_CREATED
)
def create_habit(
    payload: schemas.HabitCreate, db: DbSession
) -> schemas.HabitRead:
    """создает привычку"""
    habit = habit_service.create_habit(db, payload)
    return schemas.HabitRead.model_validate(habit)


@router.get("", response_model=list[schemas.HabitListItem])
def list_habits(db: DbSession) -> list[schemas.HabitListItem]:
    """возвращает список привычек"""
    return habit_service.list_habits(db)


@router.get("/aggregated-stats", response_model=schemas.HabitAggregateStats)
def aggregated_stats(db: DbSession) -> schemas.HabitAggregateStats:
    """возвращает агрегированную статистику"""
    return habit_service.get_aggregate_stats(db)


@router.patch(
    "/{habit_id}/archive", response_model=schemas.HabitArchiveResponse
)
def archive_habit(
    habit_id: int, db: DbSession
) -> schemas.HabitArchiveResponse:
    """архивирует привычку"""
    habit = habit_service.archive_habit(db, habit_id)
    return schemas.HabitArchiveResponse(id=habit.id, is_active=habit.is_active)


@router.post(
    "/{habit_id}/completions",
    response_model=schemas.CompletionRead,
    status_code=status.HTTP_201_CREATED,
)
def add_completion(
    habit_id: int,
    payload: schemas.CompletionCreate,
    db: DbSession,
) -> schemas.CompletionRead:
    """добавляет отметку выполнения"""
    completion = habit_service.add_completion(
        db, habit_id, payload.completed_on
    )
    return schemas.CompletionRead.model_validate(completion)


@router.get(
    "/{habit_id}/completions", response_model=list[schemas.CompletionRead]
)
def list_completions(
    habit_id: int, db: DbSession
) -> list[schemas.CompletionRead]:
    """возвращает список выполнений по датам"""
    completions = habit_service.list_completions(db, habit_id)
    return [
        schemas.CompletionRead.model_validate(item) for item in completions
    ]


@router.get("/{habit_id}/stats", response_model=schemas.HabitStats)
def habit_stats(habit_id: int, db: DbSession) -> schemas.HabitStats:
    """возвращает статистику по привычке"""
    return habit_service.get_habit_stats(db, habit_id)
