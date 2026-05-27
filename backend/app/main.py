from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.error_handlers import register_error_handlers
from app.core.logging import configure_logging
from app.routers.auth import router as auth_router
from app.routers.health import APP_VERSION, router as health_router
from app.routers.master import router as master_router
from app.routers.password import router as password_router


settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name, version=APP_VERSION)
register_error_handlers(app)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(password_router)
app.include_router(master_router)


@app.get("/")
def get_root() -> dict[str, str]:
    return {
        "app_name": settings.app_name,
        "status": "ok",
        "version": APP_VERSION,
    }
