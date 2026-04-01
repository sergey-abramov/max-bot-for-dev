from __future__ import annotations

import logging
from typing import Any

from services.application.max_handlers.common import send_text
from services.integrations.max_api_client import MaxApiClient

logger = logging.getLogger(__name__)


async def handle_bot_started(update: dict[str, Any], max_api_client: MaxApiClient) -> None:
  logger.info("MAX webhook: bot_started handled", extra={"update": update})
  await send_text(max_api_client, update, "Привет! Я запущен и готов помочь. Напишите /start.")
