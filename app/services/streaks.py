from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable


def calculate_streaks(
    completed_dates: Iterable[date], today: date | None = None
) -> tuple[int, int]:
    """считает текущую и лучшую серию по ежедневным отметкам"""
    unique_dates = sorted(set(completed_dates))
    if not unique_dates:
        return 0, 0

    if today is None:
        today = date.today()

    best_streak = 1
    running_streak = 1

    for previous, current in zip(unique_dates, unique_dates[1:], strict=False):
        if current - previous == timedelta(days=1):
            running_streak += 1
        else:
            best_streak = max(best_streak, running_streak)
            running_streak = 1

    best_streak = max(best_streak, running_streak)

    latest = unique_dates[-1]
    if latest < today - timedelta(days=1):
        return 0, best_streak

    current_streak = 1
    cursor = latest

    for previous in reversed(unique_dates[:-1]):
        if cursor - previous == timedelta(days=1):
            current_streak += 1
            cursor = previous
        else:
            break

    return current_streak, best_streak
