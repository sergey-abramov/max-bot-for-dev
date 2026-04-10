"""Module for services/quiz service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from db.models import Question, Topic, User
from db.repositories import question_repo, stat_repo, topic_repo, user_repo
from db.repositories.stat_repo import TopicStats


@dataclass(slots=True)
class QuestionView:
  """
  Представление вопроса для использования в хендлерах.
  """

  id: int
  topic: Topic
  text: str
  options: dict[str, str] | None
  correct_key: str | None
  difficulty: Optional[int]


@dataclass(slots=True)
class AnswerResult:
  """
  Результат ответа пользователя.
  """

  user: User
  question: Question
  is_correct: bool
  correct_key: str | None
  topic_stats: Optional[TopicStats]


def register_or_update_user(
  session: Session,
  *,
  telegram_id: int,
  username: Optional[str] = None,
  first_name: Optional[str] = None,
  last_name: Optional[str] = None,
) -> User:
  """
  Регистрирует или обновляет пользователя по Telegram ID.
  """
  return user_repo.get_or_create_user(
    session=session,
    telegram_id=telegram_id,
    username=username,
    first_name=first_name,
    last_name=last_name,
  )


def list_active_topics(session: Session) -> list[Topic]:
  """
  Возвращает список активных тем.
  """
  return topic_repo.get_active_topics(session=session)


def get_topic_by_slug(
  session: Session,
  slug: str,
) -> Optional[Topic]:
  """
  Возвращает тему по ее slug.
  """
  return topic_repo.get_topic_by_slug(session=session, slug=slug)


def get_random_question_for_topic(
  session: Session,
  *,
  topic_id: int,
  difficulty: Optional[int] = None,
) -> Optional[QuestionView]:
  """
  Возвращает случайный активный вопрос по теме в удобном для хендлеров виде.
  """
  topic = topic_repo.get_topic_by_id(session=session, topic_id=topic_id)
  if topic is None or not topic.is_active:
    return None

  question = question_repo.get_random_question_by_topic(
    session=session,
    topic_id=topic_id,
    difficulty=difficulty,
  )

  if question is None:
    return None

  return QuestionView(
    id=question.id,
    topic=topic,
    text=question.text,
    options=question.options,
    correct_key=question.correct_key,
    difficulty=question.difficulty,
  )


def _ensure_question_exists(
  session: Session,
  question_id: int,
) -> Question:
  """Perform ensure question exists."""
  question = question_repo.get_question_by_id(session=session, question_id=question_id)
  if question is None:
    msg = f"Question with id={question_id} not found"
    raise ValueError(msg)
  return question


def submit_answer(
  session: Session,
  *,
  telegram_id: int,
  question_id: int,
  selected_key: Optional[str],
  username: Optional[str] = None,
  first_name: Optional[str] = None,
  last_name: Optional[str] = None,
) -> AnswerResult:
  """
  Фиксирует ответ пользователя и возвращает результат проверки и агрегированную статистику по теме.
  """
  user = register_or_update_user(
    session=session,
    telegram_id=telegram_id,
    username=username,
    first_name=first_name,
    last_name=last_name,
  )

  question = _ensure_question_exists(session=session, question_id=question_id)

  correct_key = question.correct_key

  is_correct = False
  if correct_key is None:
    is_correct = False
  else:
    is_correct = selected_key == correct_key

  stat_repo.record_user_answer(
    session=session,
    user_id=user.id,
    question_id=question.id,
    is_correct=is_correct,
  )

  topic_stats: Optional[TopicStats] = None
  if question.topic_id is not None:
    topic_stats = stat_repo.get_user_topic_stats(
      session=session,
      user_id=user.id,
      topic_id=question.topic_id,
    )

  return AnswerResult(
    user=user,
    question=question,
    is_correct=is_correct,
    correct_key=correct_key,
    topic_stats=topic_stats,
  )

