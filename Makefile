up:
	docker compose up --build

down:
	docker compose down

down-clean:
	docker compose down -v

logs:
	docker compose logs -f

ps:
	docker compose ps

up-db:
	docker compose up -d db

test:
	TEST_DATABASE_URL=$${TEST_DATABASE_URL:-postgresql+psycopg://postgres:postgres@localhost:5432/habit_tracker_test} pytest

test-docker:
	docker compose up -d db
	docker compose run --rm \
		-e TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/habit_tracker_test \
		api pytest

migrate:
	alembic upgrade head

revision:
	alembic revision --autogenerate -m "$(message)"

run:
	uvicorn app.main:app --reload
