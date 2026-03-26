from __future__ import annotations

from fastapi import FastAPI

from services.api.routers.max_webhook import router as max_webhook_router
from services.api.routers.quiz import router as quiz_router
from services.application.max_event_dispatcher import MaxEventDispatcher
from services.core.settings import Settings, get_settings
from services.integrations.max_api_client import MaxApiClient


def create_app(settings: Settings | None = None) -> FastAPI:
  resolved_settings = settings or get_settings()
  resolved_settings.validate_webhook_runtime()
  app = FastAPI(title="Quiz Service API", version="1.0.0")

  app.state.settings = resolved_settings
  app.state.max_api_client = MaxApiClient(bot_token=resolved_settings.max_bot_token)
  app.state.max_event_dispatcher = MaxEventDispatcher()

  app.include_router(quiz_router)
  app.include_router(max_webhook_router, prefix=resolved_settings.max_webhook_path)
  return app
