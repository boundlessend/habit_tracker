from __future__ import annotations

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app import models, schemas
from app.services.streaks import calculate_streaks


def get_habit_or_404(db: Session, habit_id: int) -> models.Habit:
    """возвращает привычку или ошибку 404"""
    habit = db.get(models.Habit, habit_id)
    if habit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Привычка не найдена"
        )
    return habit


def create_habit(db: Session, payload: schemas.HabitCreate) -> models.Habit:
    """создает привычку"""
    habit = models.Habit(
        name=payload.name,
        description=payload.description,
        category=payload.category,
    )
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return habit


def archive_habit(db: Session, habit_id: int) -> models.Habit:
    """архивирует привычку"""
    habit = get_habit_or_404(db, habit_id)
    habit.is_active = False
    db.commit()
    db.refresh(habit)
    return habit


def add_completion(
    db: Session, habit_id: int, completed_on: date
) -> models.HabitCompletion:
    """добавляет отметку выполнения"""
    habit = get_habit_or_404(db, habit_id)

    if completed_on > date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя отмечать выполнение в будущую дату",
        )

    if not habit.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя отметить выполнение архивной привычки",
        )

    completion = models.HabitCompletion(
        habit_id=habit_id, completed_on=completed_on
    )
    db.add(completion)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Отметка за эту дату уже существует",
        ) from None

    db.refresh(completion)
    return completion


def list_completions(
    db: Session, habit_id: int
) -> list[models.HabitCompletion]:
    """возвращает список отметок по привычке"""
    get_habit_or_404(db, habit_id)
    stmt = (
        select(models.HabitCompletion)
        .where(models.HabitCompletion.habit_id == habit_id)
        .order_by(models.HabitCompletion.completed_on.desc())
    )
    return list(db.scalars(stmt))


def build_habit_stats(habit: models.Habit) -> schemas.HabitStats:
    """собирает статистику по привычке"""
    completion_dates = [
        completion.completed_on for completion in habit.completions
    ]
    current_streak, best_streak = calculate_streaks(completion_dates)
    last_completed_on = max(completion_dates) if completion_dates else None

    return schemas.HabitStats(
        habit_id=habit.id,
        name=habit.name,
        is_active=habit.is_active,
        total_completions=len(completion_dates),
        current_streak=current_streak,
        best_streak=best_streak,
        last_completed_on=last_completed_on,
    )


def get_habit_stats(db: Session, habit_id: int) -> schemas.HabitStats:
    """возвращает статистику по привычке"""
    stmt = (
        select(models.Habit)
        .options(selectinload(models.Habit.completions))
        .where(models.Habit.id == habit_id)
    )
    habit = db.scalar(stmt)
    if habit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Привычка не найдена"
        )
    return build_habit_stats(habit)


def list_habits(db: Session) -> list[schemas.HabitListItem]:
    """возвращает список привычек с текущими показателями"""
    stmt = (
        select(models.Habit)
        .options(selectinload(models.Habit.completions))
        .order_by(models.Habit.id)
    )
    habits = list(db.scalars(stmt))

    items: list[schemas.HabitListItem] = []
    for habit in habits:
        stats = build_habit_stats(habit)
        items.append(
            schemas.HabitListItem(
                id=habit.id,
                name=habit.name,
                is_active=habit.is_active,
                current_streak=stats.current_streak,
                best_streak=stats.best_streak,
                total_completions=stats.total_completions,
            )
        )
    return items


def get_aggregate_stats(db: Session) -> schemas.HabitAggregateStats:
    """возвращает агрегированную статистику по всем привычкам"""
    stmt = (
        select(models.Habit)
        .options(selectinload(models.Habit.completions))
        .order_by(models.Habit.id)
    )
    habits = list(db.scalars(stmt))

    total_completions = 0
    max_best_streak = 0
    active_habits = 0

    for habit in habits:
        if habit.is_active:
            active_habits += 1
        stats = build_habit_stats(habit)
        total_completions += stats.total_completions
        max_best_streak = max(max_best_streak, stats.best_streak)

    total_habits = len(habits)
    return schemas.HabitAggregateStats(
        total_habits=total_habits,
        active_habits=active_habits,
        archived_habits=total_habits - active_habits,
        total_completions=total_completions,
        max_best_streak=max_best_streak,
    )
