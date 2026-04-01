from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import urlencode

from services.integrations.max_api_client import MaxApiClient

logger = logging.getLogger(__name__)


def extract_reply_target(update: dict[str, Any]) -> dict[str, str]:
  payload = update.get("payload") or {}
  message = payload.get("message") or update.get("message") or {}
  recipient = message.get("recipient") or payload.get("recipient") or {}
  chat = recipient.get("chat") or payload.get("chat") or message.get("chat") or {}
  peer = payload.get("peer") or {}
  dialog = payload.get("dialog") or {}
  sender = message.get("sender") or payload.get("sender") or {}

  chat_id = (
    recipient.get("chat_id")
    or message.get("chat_id")
    or chat.get("chat_id")
    or peer.get("chat_id")
    or dialog.get("chat_id")
    or (peer.get("chat") or {}).get("chat_id")
    or (dialog.get("chat") or {}).get("chat_id")
    or payload.get("chat_id")
    or update.get("chat_id")
  )
  if chat_id is not None:
    return {"chat_id": str(chat_id)}

  user = extract_user(update)
  user_id = (
    sender.get("user_id")
    or recipient.get("user_id")
    or payload.get("user_id")
    or message.get("user_id")
    or (message.get("body") or {}).get("user_id")
    or (message.get("body") or {}).get("sender_id")
    or user.get("user_id")
    or update.get("user_id")
  )
  if user_id is not None:
    return {"user_id": str(user_id)}
  return {}


def extract_user(update: dict[str, Any]) -> dict[str, Any]:
  payload = update.get("payload") or {}
  message = payload.get("message") or update.get("message") or {}
  sender = message.get("sender") or payload.get("sender") or {}
  if isinstance(sender, dict) and sender:
    return sender
  body = message.get("body") or {}
  body_user = body.get("user")
  if isinstance(body_user, dict) and body_user:
    return body_user
  update_user = update.get("user")
  if isinstance(update_user, dict) and update_user:
    return update_user
  return {}


def extract_user_id(update: dict[str, Any]) -> str:
  payload = update.get("payload") or {}
  message = payload.get("message") or update.get("message") or {}
  body = message.get("body") or {}
  recipient = message.get("recipient") or payload.get("recipient") or {}
  sender = message.get("sender") or payload.get("sender") or {}
  user = extract_user(update)

  candidates = [
    user.get("user_id") if isinstance(user, dict) else None,
    sender.get("user_id") if isinstance(sender, dict) else None,
    body.get("user_id") if isinstance(body, dict) else None,
    (body.get("user") or {}).get("user_id") if isinstance(body, dict) and isinstance(body.get("user"), dict) else None,
    recipient.get("user_id") if isinstance(recipient, dict) else None,
    payload.get("user_id"),
    update.get("user_id"),
    (update.get("message") or {}).get("user_id") if isinstance(update.get("message"), dict) else None,
  ]
  for value in candidates:
    if value is None:
      continue
    text = str(value).strip()
    if text:
      return text
  return ""


def extract_message_text(update: dict[str, Any]) -> str:
  payload = update.get("payload") or {}
  message = payload.get("message") or update.get("message") or {}
  body = message.get("body") or {}
  text = body.get("text") or payload.get("text") or update.get("text") or ""
  return str(text).strip()


def extract_callback_payload(update: dict[str, Any]) -> str:
  payload = update.get("payload") or {}
  message = update.get("message") or {}
  callback = payload.get("callback") or update.get("callback") or {}
  candidates = [
    (message.get("callback") or {}).get("payload") if isinstance(message.get("callback"), dict) else None,
    message.get("callback_payload"),
    message.get("data"),
    callback.get("payload") if isinstance(callback, dict) else None,
    payload.get("callback_payload"),
    payload.get("data"),
    payload.get("payload"),
    update.get("callback_payload"),
  ]
  for value in candidates:
    if value is None:
      continue
    text = str(value).strip()
    if text:
      return text
  return ""


def dump_identity(update: dict[str, Any]) -> str:
  user = extract_user(update)
  target = extract_reply_target(update)
  return (
    "Отладка identity:\n"
    f"- user_id: {extract_user_id(update) or 'не найден'}\n"
    f"- reply_target: {json.dumps(target, ensure_ascii=False) if target else 'не найден'}\n"
    f"- user: {json.dumps(user, ensure_ascii=False) if user else '{}'}"
  )


async def send_text(max_api_client: MaxApiClient, update: dict[str, Any], text: str) -> None:
  await send_message(max_api_client, update, text=text)


async def send_message(
  max_api_client: MaxApiClient,
  update: dict[str, Any],
  *,
  text: str,
  attachments: list[dict[str, Any]] | None = None,
) -> None:
  target = extract_reply_target(update)
  if not target:
    logger.warning("MAX webhook: reply target missing, cannot send message", extra={"update": update})
    return
  query = urlencode(target)
  body: dict[str, Any] = {"text": text}
  if attachments:
    body["attachments"] = attachments
  await max_api_client.post(f"/messages?{query}", body)

