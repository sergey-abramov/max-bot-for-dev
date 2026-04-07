from __future__ import annotations

import logging
import time
from threading import Lock
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from services.application.max_event_dispatcher import MaxEventDispatcher
from services.core.settings import Settings

logger = logging.getLogger(__name__)

router = APIRouter()

_SEEN_EVENT_IDS: dict[str, float] = {}
_SEEN_LOCK = Lock()
_DEDUP_TTL_SECONDS = 300


def _extract_event_id(payload: dict) -> Optional[str]:
  event_id = payload.get("update_id") or payload.get("event_id")
  if event_id is None:
    return None
  value = str(event_id).strip()
  return value or None


def _is_duplicate(event_id: str) -> bool:
  now = time.time()
  with _SEEN_LOCK:
    # Compact stale keys on write path to keep memory bounded.
    expired = [key for key, ts in _SEEN_EVENT_IDS.items() if now - ts > _DEDUP_TTL_SECONDS]
    for key in expired:
      _SEEN_EVENT_IDS.pop(key, None)

    if event_id in _SEEN_EVENT_IDS:
      return True

    _SEEN_EVENT_IDS[event_id] = now
    return False


@router.post("")
async def receive_webhook(
  request: Request,
) -> dict:
  settings: Settings = request.app.state.settings
  dispatcher: MaxEventDispatcher = request.app.state.max_event_dispatcher

  try:
    payload = await request.json()
  except Exception as exc:
    raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

  if not isinstance(payload, dict):
    raise HTTPException(status_code=400, detail="Invalid payload type")

  event_id = _extract_event_id(payload)
  update_type = payload.get("update_type")

  logger.info(
    "MAX webhook request received: event_id=%s update_type=%s payload=%s",
    event_id,
    update_type,
    payload,
  )

  if event_id and _is_duplicate(event_id):
    logger.info("MAX webhook: duplicate update ignored", extra={"event_id": event_id})
    return {"ok": True, "deduplicated": True}

  try:
    await dispatcher.dispatch(payload)
  except Exception:
    logger.exception("MAX webhook: dispatcher failed", extra={"event_id": event_id})
    raise HTTPException(status_code=500, detail="Webhook dispatch failed")

  return {"ok": True}
