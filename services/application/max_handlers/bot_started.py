from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def handle_bot_started(update: dict[str, Any]) -> None:
  logger.info("MAX webhook: bot_started handled", extra={"update": update})
