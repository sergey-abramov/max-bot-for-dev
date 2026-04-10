"""Module for db/repositories/stat repo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import Question, Topic, UserQuestionStat


@dataclass(slots=True)
class TopicStats:
  """Represent topicstats."""
  topic: Topic
  correct_count: int
  wrong_count: int
  last_activity_at: Optional[datetime]

  @property
  def total_answers(self) -> int:
    """Perform total answers."""
    return self.correct_count + self.wrong_count


def record_user_answer(
  session: Session,
  *,
  user_id: int,
  question_id: int,
  is_correct: bool,
) -> UserQuestionStat:
  """
  Создает запись статистики ответа пользователя на вопрос.
  """
  stat = UserQuestionStat(
    user_id=user_id,
    question_id=question_id,
    is_correct=is_correct,
  )
  session.add(stat)
  session.flush()
  return stat


def get_user_topic_stats(
  session: Session,
  *,
  user_id: int,
  topic_id: int,
) -> Optional[TopicStats]:
  """
  Возвращает агрегированную статистику пользователя по теме.
  """
  stmt = (
    select(
      Topic,
      func.count().filter(UserQuestionStat.is_correct.is_(True)).label(
        "correct_count",
      ),
      func.count().filter(UserQuestionStat.is_correct.is_(False)).label(
        "wrong_count",
      ),
      func.max(UserQuestionStat.answered_at).label("last_activity_at"),
    )
    .join(Question, Question.id == UserQuestionStat.question_id)
    .join(Topic, Topic.id == Question.topic_id)
    .where(
      UserQuestionStat.user_id == user_id,
      Topic.id == topic_id,
    )
    .group_by(Topic.id)
  )

  row = session.execute(stmt).one_or_none()

  if row is None:
    topic = session.scalar(select(Topic).where(Topic.id == topic_id))
    if topic is None:
      return None
    return TopicStats(
      topic=topic,
      correct_count=0,
      wrong_count=0,
      last_activity_at=None,
    )

  topic, correct_count, wrong_count, last_activity_at = row

  return TopicStats(
    topic=topic,
    correct_count=int(correct_count or 0),
    wrong_count=int(wrong_count or 0),
    last_activity_at=last_activity_at,
  )

