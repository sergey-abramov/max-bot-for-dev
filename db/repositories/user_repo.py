"""Module for db/repositories/user repo."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import User


def get_user_by_telegram_id(
  session: Session,
  telegram_id: int,
) -> Optional[User]:
  """
  Возвращает пользователя по его Telegram ID или None, если не найден.
  """
  stmt = select(User).where(User.telegram_id == telegram_id)
  return session.scalar(stmt)


def get_user_by_id(
  session: Session,
  user_id: int,
) -> Optional[User]:
  """
  Возвращает пользователя по его внутреннему ID или None.
  """
  stmt = select(User).where(User.id == user_id)
  return session.scalar(stmt)


def get_or_create_user(
  session: Session,
  telegram_id: int,
  username: Optional[str] = None,
  first_name: Optional[str] = None,
  last_name: Optional[str] = None,
) -> User:
  """
  Находит пользователя по Telegram ID или создает нового.

  При наличии новых значений username/first_name/last_name обновляет существующую запись.
  """
  user = get_user_by_telegram_id(session=session, telegram_id=telegram_id)

  if user is None:
    user = User(
      telegram_id=telegram_id,
      username=username,
      first_name=first_name,
      last_name=last_name,
    )
    session.add(user)
    session.flush()
    return user

  updated = False

  if username is not None and username != user.username:
    user.username = username
    updated = True

  if first_name is not None and first_name != user.first_name:
    user.first_name = first_name
    updated = True

  if last_name is not None and last_name != user.last_name:
    user.last_name = last_name
    updated = True

  if updated:
    session.flush()

  return user

