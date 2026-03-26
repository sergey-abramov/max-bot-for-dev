from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def handle_message_callback(update: dict[str, Any]) -> None:
  logger.info("MAX webhook: message_callback handled", extra={"update": update})
