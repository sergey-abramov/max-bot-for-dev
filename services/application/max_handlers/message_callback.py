from __future__ import annotations

import logging
from typing import Any

from services.integrations.max_api_client import MaxApiClient

logger = logging.getLogger(__name__)


async def handle_message_callback(update: dict[str, Any], max_api_client: MaxApiClient) -> None:
  _ = max_api_client
  logger.info("MAX webhook: message_callback handled", extra={"update": update})
