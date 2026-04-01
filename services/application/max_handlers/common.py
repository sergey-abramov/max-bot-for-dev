from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from services.integrations.max_api_client import MaxApiClient


def extract_reply_target(update: dict[str, Any]) -> dict[str, str]:
  payload = update.get("payload") or {}
  message = payload.get("message") or {}
  recipient = message.get("recipient") or payload.get("recipient") or {}
  chat = recipient.get("chat") or payload.get("chat") or {}
  sender = message.get("sender") or payload.get("sender") or {}

  chat_id = (
    recipient.get("chat_id")
    or message.get("chat_id")
    or chat.get("chat_id")
    or payload.get("chat_id")
  )
  if chat_id is not None:
    return {"chat_id": str(chat_id)}

  user_id = sender.get("user_id") or recipient.get("user_id") or payload.get("user_id")
  if user_id is not None:
    return {"user_id": str(user_id)}
  return {}


def extract_user(update: dict[str, Any]) -> dict[str, Any]:
  payload = update.get("payload") or {}
  message = payload.get("message") or {}
  sender = message.get("sender") or payload.get("sender") or {}
  return sender if isinstance(sender, dict) else {}


def extract_user_id(update: dict[str, Any]) -> str:
  user = extract_user(update)
  user_id = user.get("user_id")
  return str(user_id).strip() if user_id is not None else ""


def extract_message_text(update: dict[str, Any]) -> str:
  payload = update.get("payload") or {}
  message = payload.get("message") or {}
  body = message.get("body") or {}
  text = body.get("text") or payload.get("text") or update.get("text") or ""
  return str(text).strip()


def extract_callback_payload(update: dict[str, Any]) -> str:
  payload = update.get("payload") or {}
  callback = payload.get("callback") or update.get("callback") or {}
  candidates = [
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


async def send_text(max_api_client: MaxApiClient, update: dict[str, Any], text: str) -> None:
  target = extract_reply_target(update)
  if not target:
    return
  query = urlencode(target)
  await max_api_client.post(f"/messages?{query}", {"text": text})

