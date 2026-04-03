from __future__ import annotations

from collections.abc import Generator
import os
from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _build_test_database_url() -> str:
    """возвращает url тестовой базы данных"""
    return os.getenv(
        'TEST_DATABASE_URL',
        'postgresql+psycopg://postgres:postgres@localhost:5432/habit_tracker_test',
    )


def _build_admin_database_url(database_url: str) -> str:
    """возвращает url служебной базы данных postgres"""
    url = make_url(database_url)
    admin_url = URL.create(
        drivername=url.drivername,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        database='postgres',
        query=url.query,
    )
    return admin_url.render_as_string(hide_password=False)


TEST_DATABASE_URL = _build_test_database_url()
TEST_DATABASE_NAME = make_url(TEST_DATABASE_URL).database
ADMIN_DATABASE_URL = _build_admin_database_url(TEST_DATABASE_URL)

os.environ['DATABASE_URL'] = TEST_DATABASE_URL

from app.db import get_db
from app.main import app

engine = create_engine(TEST_DATABASE_URL, future=True)
TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def _quote_identifier(value: str) -> str:
    """экранирует имя базы данных для sql"""
    return value.replace('"', '""')


def _recreate_test_database() -> None:
    """пересоздает тестовую базу данных"""
    if TEST_DATABASE_NAME is None:
        raise RuntimeError('Не удалось определить имя тестовой базы данных')
    if TEST_DATABASE_NAME == 'postgres':
        raise RuntimeError('Нельзя использовать postgres как тестовую базу данных')

    admin_engine = create_engine(
        ADMIN_DATABASE_URL,
        isolation_level='AUTOCOMMIT',
        future=True,
    )
    quoted_database_name = _quote_identifier(TEST_DATABASE_NAME)
    with admin_engine.connect() as connection:
        connection.execute(
            text(
                'SELECT pg_terminate_backend(pid) '
                'FROM pg_stat_activity '
                'WHERE datname = :database_name AND pid <> pg_backend_pid()'
            ),
            {'database_name': TEST_DATABASE_NAME},
        )
        connection.execute(
            text(f'DROP DATABASE IF EXISTS "{quoted_database_name}"')
        )
        connection.execute(text(f'CREATE DATABASE "{quoted_database_name}"'))
    admin_engine.dispose()


def _drop_test_database() -> None:
    """удаляет тестовую базу данных"""
    if TEST_DATABASE_NAME is None or TEST_DATABASE_NAME == 'postgres':
        return

    admin_engine = create_engine(
        ADMIN_DATABASE_URL,
        isolation_level='AUTOCOMMIT',
        future=True,
    )
    quoted_database_name = _quote_identifier(TEST_DATABASE_NAME)
    with admin_engine.connect() as connection:
        connection.execute(
            text(
                'SELECT pg_terminate_backend(pid) '
                'FROM pg_stat_activity '
                'WHERE datname = :database_name AND pid <> pg_backend_pid()'
            ),
            {'database_name': TEST_DATABASE_NAME},
        )
        connection.execute(
            text(f'DROP DATABASE IF EXISTS "{quoted_database_name}"')
        )
    admin_engine.dispose()


def _apply_migrations() -> None:
    """применяет миграции alembic к тестовой базе данных"""
    alembic_config = Config(str(ROOT_DIR / 'alembic.ini'))
    alembic_config.set_main_option('script_location', str(ROOT_DIR / 'alembic'))
    alembic_config.set_main_option('sqlalchemy.url', TEST_DATABASE_URL)

    previous_database_url = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = TEST_DATABASE_URL
    try:
        command.upgrade(alembic_config, 'head')
    finally:
        if previous_database_url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = previous_database_url


@pytest.fixture(scope='session', autouse=True)
def setup_database() -> Generator[None, None, None]:
    """готовит тестовую базу данных и накатывает миграции"""
    _recreate_test_database()
    _apply_migrations()

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    required_tables = {'habits', 'habit_completions'}
    missing_tables = required_tables - existing_tables
    if missing_tables:
        missing_list = ', '.join(sorted(missing_tables))
        raise RuntimeError(
            f'В тестовой базе не созданы таблицы: {missing_list}'
        )

    yield

    engine.dispose()
    _drop_test_database()


@pytest.fixture(autouse=True)
def clean_database(setup_database: None) -> Generator[None, None, None]:
    """очищает таблицы между тестами"""
    with engine.begin() as connection:
        connection.execute(
            text(
                'TRUNCATE TABLE habit_completions, habits '
                'RESTART IDENTITY CASCADE'
            )
        )
    yield


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """создает сессию для тестов"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """создает тестовый клиент fastapi"""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
