from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def handle_message_created(update: dict[str, Any]) -> None:
  logger.info("MAX webhook: message_created handled", extra={"update": update})
