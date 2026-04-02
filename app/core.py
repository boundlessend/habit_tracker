from functools import lru_cache
import os


class Settings:
    """хранит настройки приложения"""

    app_name: str = "Трекер привычек"
    api_prefix: str = "/api/v1"
    database_url: str

    def __init__(self) -> None:
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@db:5432/habit_tracker",
        )


@lru_cache
def get_settings() -> Settings:
    """возвращает настройки приложения"""
    return Settings()
