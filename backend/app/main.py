from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.routers.health import APP_VERSION, router as health_router


settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name, version=APP_VERSION)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health_router)


@app.get("/")
def get_root() -> dict[str, str]:
    return {
        "app_name": settings.app_name,
        "status": "ok",
        "version": APP_VERSION,
    }
