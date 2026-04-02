# Habit Tracker API

## что есть

- создание привычки;
- архивирование привычки;
- отметка выполнения привычки за конкретную дату;
- список выполнений по датам;
- статистика по одной привычке;
- список привычек с текущими показателями;
- агрегированная статистика по всем привычкам;
- хранение данных в PostgreSQL;
- миграции через Alembic;
- небольшой набор pytest-тестов;
- Dockerfile, docker compose и Makefile.

## что внутри

- Python
- FastAPI
- Pydantic
- uvicorn
- PostgreSQL
- Alembic
- SQLAlchemy
- pytest

## Структура проекта

```text
habit-tracker/
├── alembic/
├── app/
│   ├── api/
│   ├── services/
│   ├── core.py
│   ├── db.py
│   ├── main.py
│   ├── models.py
│   └── schemas.py
├── tests/
├── .env.example
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── requirements.txt
└── README.md
```

## запуск через docker compose

### как поднять сервис и базу

```bash
make up
```

или без `make`:

```bash
docker compose up --build
```

### как проверить, что сервис поднялся

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:

```json
{"status":"ok"}
```

### как открыть документацию

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### как остановить остановить проект

```bash
make down
```

## запуск без Docker

### 1. установить зависимости

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. поднять PostgreSQL

пример строки подключения:

```bash
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/habit_tracker
```

### 3. применить миграции

```bash
alembic upgrade head
```

### 4. запустить приложение

```bash
uvicorn app.main:app --reload
```

## makefile

основные команды:

```bash
make up           # поднять postgres и api
make down         # остановить контейнеры
make logs         # посмотреть логи
make ps           # посмотреть статус контейнеров
make test         # запустить pytest локально
make test-docker  # запустить pytest в docker
make migrate      # применить миграции
make revision message="add table"  # создать новую миграцию
make run          # локальный запуск uvicorn
```

## проверки после запуска

### Проверка healthcheck

```bash
curl http://localhost:8000/health
```

### создать привычку

```bash
curl -X POST http://localhost:8000/api/v1/habits \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Читать 20 страниц",
    "description": "каждый вечер",
    "category": "обучение"
  }'
```

### отметить выполнение

```bash
curl -X POST http://localhost:8000/api/v1/habits/1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "completed_on": "2026-04-02"
  }'
```

### посмотреть статистику по привычке

```bash
curl http://localhost:8000/api/v1/habits/1/stats
```

### получить список привычек

```bash
curl http://localhost:8000/api/v1/habits
```

### получить список выполнений

```bash
curl http://localhost:8000/api/v1/habits/1/completions
```

### архивировать привычку

```bash
curl -X PATCH http://localhost:8000/api/v1/habits/1/archive
```

### получить агрегированную статистику

```bash
curl http://localhost:8000/api/v1/habits/aggregated-stats
```

## команды для проверок

### тесты

```bash
pytest
```

или:

```bash
make test
```

### прогнать тесты в docker

```bash
make test-docker
```

### применить миграции

```bash
alembic upgrade head
```

или:

```bash
make migrate
```

### создать новую миграцию

```bash
alembic revision --autogenerate -m "add some change"
```

или:

```bash
make revision message="add some change"
```

## сценариев ручной проверки

1. **Создать привычку с валидными данными**  
   Ожидаемо: `201 Created`, в ответе есть `id`, `name`, `is_active=true`.

2. **Создать привычку с пустым названием**  
   Отправить `name: "   "`.  
   Ожидаемо: `422 Unprocessable Entity`, валидация сообщает, что название не должно быть пустым.

3. **Отметить выполнение существующей привычки**  
   Передать дату не из будущего.  
   Ожидаемо: `201 Created`.

4. **Повторно отметить ту же дату**  
   Повторить запрос с тем же `habit_id` и `completed_on`.  
   Ожидаемо: `400 Bad Request`, сообщение: `Отметка за эту дату уже существует`.

5. **Отметить несуществующую привычку**  
   Отправить запрос на несуществующий `habit_id`.  
   Ожидаемо: `404 Not Found`, сообщение: `Привычка не найдена`.

6. **Отправить будущую дату**  
   Передать дату больше текущей даты сервера.  
   Ожидаемо: `400 Bad Request`, сообщение: `Нельзя отмечать выполнение в будущую дату`.

7. **Архивировать привычку и попытаться отметить ее снова**  
   Сначала вызвать архивирование, затем попробовать добавить выполнение.  
   Ожидаемо: `400 Bad Request`, сообщение: `Нельзя отметить выполнение архивной привычки`.

## как считаются текущая и лучшая серия

### лучшая серия

беру все уникальные даты выполнения и сортирую по возрастанию

дальше ищу самый длинный непрерывный отрезок, где каждая следующая дата идет ровно на один день после предыдущей

пример:

- `2026-04-01`
- `2026-04-02`
- `2026-04-03`
- `2026-04-05`

лучшая серия равна `3`, потому что подряд идут только первые три даты

### текущая серия

текущая серия считается от последней даты выполнения назад

правила следующие:

- если последняя отметка была **сегодня** или **вчера**, серия считается активной;
- если последняя отметка была раньше, текущая серия считается равной `0`.

после этого от последней даты выполнение проверяется назад по одному дню
пока даты идут подряд без пропусков, серия растет

пример 1:

- сегодня `2026-04-04`
- отметки: `2026-04-02`, `2026-04-03`
- текущая серия = `2`

пример 2:

- сегодня `2026-04-04`
- отметки: `2026-03-30`, `2026-03-31`
- текущая серия = `0`, потому что серия уже прервалась