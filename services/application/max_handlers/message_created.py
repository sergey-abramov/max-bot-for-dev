from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

from services.integrations.max_api_client import MaxApiClient

logger = logging.getLogger(__name__)


def _extract_message_text(update: dict[str, Any]) -> str:
  payload = update.get("payload") or {}
  message = payload.get("message") or {}
  body = message.get("body") or {}
  text = body.get("text") or payload.get("text") or update.get("text") or ""
  return str(text).strip()


def _extract_reply_target(update: dict[str, Any]) -> dict[str, str]:
  payload = update.get("payload") or {}
  message = payload.get("message") or {}
  recipient = message.get("recipient") or payload.get("recipient") or {}
  chat = recipient.get("chat") or payload.get("chat") or {}
  sender = message.get("sender") or payload.get("sender") or {}

  chat_id = recipient.get("chat_id") or message.get("chat_id") or chat.get("chat_id")
  if chat_id is not None:
    return {"chat_id": str(chat_id)}

  user_id = sender.get("user_id") or recipient.get("user_id") or payload.get("user_id")
  if user_id is not None:
    return {"user_id": str(user_id)}

  return {}


async def handle_message_created(update: dict[str, Any], max_api_client: MaxApiClient) -> None:
  logger.info("MAX webhook: message_created handled", extra={"update": update})

  text = _extract_message_text(update)
  if text != "/start":
    return

  target = _extract_reply_target(update)
  if not target:
    logger.warning("MAX webhook: /start received but reply target missing", extra={"update": update})
    return

  query = urlencode(target)
  await max_api_client.post(
    f"/messages?{query}",
    {"text": "Добро пожаловать! Бот запущен. Напишите сообщение или выберите действие в меню."},
  )
