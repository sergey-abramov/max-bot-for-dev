"""Module for db/repositories/topic repo."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Topic


def get_active_topics(session: Session) -> List[Topic]:
  """
  Возвращает список активных тем, отсортированных по заголовку.
  """
  stmt = (
    select(Topic)
    .where(Topic.is_active.is_(True))
    .order_by(Topic.title.asc())
  )
  result = session.scalars(stmt)
  return list(result.all())


def get_topic_by_slug(
  session: Session,
  slug: str,
) -> Optional[Topic]:
  """
  Возвращает тему по ее slug или None, если не найдена.
  """
  stmt = select(Topic).where(Topic.slug == slug)
  return session.scalar(stmt)


def get_topic_by_id(
  session: Session,
  topic_id: int,
) -> Optional[Topic]:
  """
  Возвращает тему по внутреннему ID или None.
  """
  stmt = select(Topic).where(Topic.id == topic_id)
  return session.scalar(stmt)

