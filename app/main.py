from fastapi import FastAPI

from app.api.routes import router as habits_router
from app.core import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.include_router(habits_router, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    """проверяет, что сервис запущен"""
    return {"status": "ok"}
