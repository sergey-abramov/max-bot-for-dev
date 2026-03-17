from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from db.session import get_session
from services import quiz_service


app = FastAPI(
  title="Quiz Service API",
  version="1.0.0",
)


class UserSyncPayload(BaseModel):
  telegram_id: int
  username: Optional[str] = None
  first_name: Optional[str] = None
  last_name: Optional[str] = None


def _user_to_dict(user) -> Dict[str, Any]:
  return {
    "id": user.id,
    "telegram_id": user.telegram_id,
    "username": user.username,
    "first_name": user.first_name,
    "last_name": user.last_name,
    "created_at": user.created_at.isoformat() if user.created_at else None,
    "updated_at": user.updated_at.isoformat() if user.updated_at else None,
  }


@app.post("/users/sync")
def sync_user(payload: UserSyncPayload) -> Dict[str, Any]:
  """
  Регистрирует или обновляет пользователя в БД по его Telegram ID.

  Этот эндпоинт предназначен для вызова из телеграм-бота при первом
  взаимодействии пользователя (например, при команде /start или запуске викторины).
  """
  with get_session() as session:
    user = quiz_service.register_or_update_user(
      session=session,
      telegram_id=payload.telegram_id,
      username=payload.username,
      first_name=payload.first_name,
      last_name=payload.last_name,
    )

    return _user_to_dict(user)

