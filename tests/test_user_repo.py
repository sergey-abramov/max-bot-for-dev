from __future__ import annotations

from db.models import User
from db.repositories.user_repo import (
  get_or_create_user,
  get_user_by_id,
  get_user_by_telegram_id,
)


def test_get_or_create_user_creates_new_user(db_session) -> None:
  telegram_id = 123456789

  user = get_or_create_user(
    session=db_session,
    telegram_id=telegram_id,
    username="testuser",
    first_name="Test",
    last_name="User",
  )

  assert isinstance(user, User)
  assert user.telegram_id == telegram_id
  assert user.username == "testuser"

  fetched_by_telegram = get_user_by_telegram_id(
    session=db_session,
    telegram_id=telegram_id,
  )
  assert fetched_by_telegram is not None
  assert fetched_by_telegram.id == user.id

  fetched_by_id = get_user_by_id(
    session=db_session,
    user_id=user.id,
  )
  assert fetched_by_id is not None
  assert fetched_by_id.telegram_id == telegram_id


def test_get_or_create_user_updates_existing(db_session) -> None:
  telegram_id = 987654321

  first = get_or_create_user(
    session=db_session,
    telegram_id=telegram_id,
    username="old_name",
    first_name="Old",
    last_name="Name",
  )

  updated = get_or_create_user(
    session=db_session,
    telegram_id=telegram_id,
    username="new_name",
    first_name="New",
    last_name="Name",
  )

  assert updated.id == first.id
  assert updated.username == "new_name"
  assert updated.first_name == "New"
  assert updated.last_name == "Name"

