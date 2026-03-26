from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from services.application.max_handlers.bot_started import handle_bot_started
from services.application.max_handlers.message_callback import handle_message_callback
from services.application.max_handlers.message_created import handle_message_created

logger = logging.getLogger(__name__)

Handler = Callable[[dict[str, Any]], Awaitable[None]]


class MaxEventDispatcher:
  def __init__(self) -> None:
    self._handlers: dict[str, Handler] = {
      "bot_started": handle_bot_started,
      "message_created": handle_message_created,
      "message_callback": handle_message_callback,
    }

  async def dispatch(self, update: dict[str, Any]) -> None:
    update_type = str(update.get("update_type") or "").strip()
    if not update_type:
      logger.warning("MAX webhook: update_type is empty")
      return

    handler = self._handlers.get(update_type)
    if handler is None:
      logger.info("MAX webhook: no handler registered", extra={"update_type": update_type})
      return

    await handler(update)
