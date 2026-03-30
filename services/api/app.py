from __future__ import annotations

import logging

from fastapi import FastAPI

from services.api.routers.max_webhook import router as max_webhook_router
from services.api.routers.quiz import router as quiz_router
from services.application.max_event_dispatcher import MaxEventDispatcher
from services.core.settings import Settings, get_settings
from services.integrations.max_api_client import MaxApiClient

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
  resolved_settings = settings or get_settings()
  resolved_settings.validate_webhook_runtime()
  app = FastAPI(title="Quiz Service API", version="1.0.0")

  app.state.settings = resolved_settings
  app.state.max_api_client = MaxApiClient(bot_token=resolved_settings.max_bot_token)
  app.state.max_event_dispatcher = MaxEventDispatcher(max_api_client=app.state.max_api_client)

  @app.on_event("startup")
  async def _register_webhook_subscription() -> None:
    if not resolved_settings.is_production():
      return
    if not resolved_settings.max_webhook_autosubscribe:
      return
    webhook_url = resolved_settings.webhook_public_url()
    if not webhook_url:
      logger.warning("MAX webhook autosubscribe skipped: PUBLIC_BASE_URL is empty")
      return
    try:
      result = await app.state.max_api_client.ensure_webhook_subscription(
        url=webhook_url,
        update_types=["message_created", "message_callback", "bot_started"],
      )
      logger.info(
        "MAX webhook autosubscribe finished",
        extra={"status": result.get("status"), "url": webhook_url},
      )
    except Exception:
      logger.exception("MAX webhook autosubscribe failed", extra={"url": webhook_url})

  app.include_router(quiz_router)
  app.include_router(max_webhook_router, prefix=resolved_settings.max_webhook_path)
  return app
