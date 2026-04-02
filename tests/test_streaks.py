from datetime import date

from app.services.streaks import calculate_streaks


def test_calculate_streaks_active_run_from_yesterday() -> None:
    current, best = calculate_streaks(
        [date(2026, 4, 1), date(2026, 4, 2), date(2026, 4, 3)],
        today=date(2026, 4, 4),
    )

    assert current == 3
    assert best == 3


def test_calculate_streaks_resets_when_run_is_broken() -> None:
    current, best = calculate_streaks(
        [
            date(2026, 3, 25),
            date(2026, 3, 26),
            date(2026, 3, 28),
            date(2026, 3, 29),
        ],
        today=date(2026, 4, 2),
    )

    assert current == 0
    assert best == 2


def test_calculate_streaks_ignores_duplicate_dates() -> None:
    current, best = calculate_streaks(
        [date(2026, 4, 1), date(2026, 4, 1), date(2026, 4, 2)],
        today=date(2026, 4, 2),
    )

    assert current == 2
    assert best == 2
