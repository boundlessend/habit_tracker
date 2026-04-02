from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core import get_settings


class Base(DeclarativeBase):
    """базовый класс для моделей sqlalchemy"""


settings = get_settings()
engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """возвращает сессию базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
