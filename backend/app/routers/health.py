from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.health import HealthResponse


APP_VERSION = "0.1.0"

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        app_env=settings.app_env,
        version=APP_VERSION,
    )
