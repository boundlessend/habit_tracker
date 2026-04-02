up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f

ps:
	docker compose ps

test:
	pytest

test-docker:
	docker compose run --rm api pytest

migrate:
	alembic upgrade head

revision:
	alembic revision --autogenerate -m "$(message)"

run:
	uvicorn app.main:app --reload
