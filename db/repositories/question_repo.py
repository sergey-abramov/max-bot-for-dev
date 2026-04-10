"""Module for db/repositories/question repo."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from db.models import Question


def _base_active_question_query() -> Select[tuple[Question]]:
  """Perform base active question query."""
  return select(Question).where(Question.is_active.is_(True))


def get_question_by_id(
  session: Session,
  question_id: int,
) -> Optional[Question]:
  """
  Возвращает вопрос по его ID или None.
  """
  stmt = _base_active_question_query().where(Question.id == question_id)
  return session.scalar(stmt)


def get_questions_by_topic(
  session: Session,
  topic_id: int,
  *,
  difficulty: Optional[int] = None,
  limit: Optional[int] = None,
) -> List[Question]:
  """
  Возвращает список активных вопросов по теме с опциональной фильтрацией по сложности.
  """
  stmt = _base_active_question_query().where(Question.topic_id == topic_id)

  if difficulty is not None:
    stmt = stmt.where(Question.difficulty == difficulty)

  stmt = stmt.order_by(Question.id.asc())

  if limit is not None:
    stmt = stmt.limit(limit)

  result = session.scalars(stmt)
  return list(result.all())


def get_random_question_by_topic(
  session: Session,
  topic_id: int,
  *,
  difficulty: Optional[int] = None,
) -> Optional[Question]:
  """
  Возвращает случайный активный вопрос по теме.
  """
  stmt = _base_active_question_query().where(Question.topic_id == topic_id)

  if difficulty is not None:
    stmt = stmt.where(Question.difficulty == difficulty)

  stmt = stmt.order_by(func.random())  # type: ignore[arg-type]

  return session.scalar(stmt)

