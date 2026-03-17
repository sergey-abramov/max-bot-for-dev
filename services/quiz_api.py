from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
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


class TopicOut(BaseModel):
  id: int
  slug: str
  title: str
  description: Optional[str] = None


class QuestionOut(BaseModel):
  id: int
  topic_id: int
  topic_slug: str
  text: str
  options: Dict[str, str]
  difficulty: Optional[int] = None


class TopicStatsOut(BaseModel):
  topic_id: int
  topic_slug: str
  correct_count: int
  wrong_count: int
  total_answers: int
  last_activity_at: Optional[datetime] = None


class SubmitAnswerPayload(BaseModel):
  telegram_id: int
  question_id: int
  selected_key: Optional[str] = None
  username: Optional[str] = None
  first_name: Optional[str] = None
  last_name: Optional[str] = None


class AnswerResultOut(BaseModel):
  is_correct: bool
  correct_key: Optional[str] = None
  question: QuestionOut
  topic_stats: Optional[TopicStatsOut] = None


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


@app.get("/topics", response_model=List[TopicOut])
def list_topics() -> List[TopicOut]:
  """
  Возвращает список активных тем викторины.
  """
  with get_session() as session:
    topics = quiz_service.list_active_topics(session=session)
    return [
      TopicOut(
        id=topic.id,
        slug=topic.slug,
        title=topic.title,
        description=topic.description,
      )
      for topic in topics
    ]


@app.get("/topics/{slug}/random-question", response_model=QuestionOut)
def get_random_question(slug: str, difficulty: Optional[int] = None) -> QuestionOut:
  """
  Возвращает случайный активный вопрос по теме.
  """
  with get_session() as session:
    topic = quiz_service.get_topic_by_slug(session=session, slug=slug)
    if topic is None or not topic.is_active:
      raise HTTPException(status_code=404, detail="Topic not found or inactive")

    question_view = quiz_service.get_random_question_for_topic(
      session=session,
      topic_id=topic.id,
      difficulty=difficulty,
    )
    if question_view is None:
      raise HTTPException(status_code=404, detail="No questions for this topic")

    options: Dict[str, str] = question_view.options or {}

    return QuestionOut(
      id=question_view.id,
      topic_id=topic.id,
      topic_slug=topic.slug,
      text=question_view.text,
      options=options,
      difficulty=question_view.difficulty,
    )


@app.post("/answers/submit", response_model=AnswerResultOut)
def submit_answer(payload: SubmitAnswerPayload) -> AnswerResultOut:
  """
  Принимает ответ пользователя на вопрос и возвращает результат проверки
  вместе с агрегированной статистикой по теме.
  """
  with get_session() as session:
    result = quiz_service.submit_answer(
      session=session,
      telegram_id=payload.telegram_id,
      question_id=payload.question_id,
      selected_key=payload.selected_key,
      username=payload.username,
      first_name=payload.first_name,
      last_name=payload.last_name,
    )

    question = result.question
    topic = question.topic

    options: Dict[str, str] = question.options or {}

    question_out = QuestionOut(
      id=question.id,
      topic_id=topic.id,
      topic_slug=topic.slug,
      text=question.text,
      options=options,
      difficulty=question.difficulty,
    )

    topic_stats_out: Optional[TopicStatsOut] = None
    if result.topic_stats is not None:
      ts = result.topic_stats
      topic_stats_out = TopicStatsOut(
        topic_id=ts.topic.id,
        topic_slug=ts.topic.slug,
        correct_count=ts.correct_count,
        wrong_count=ts.wrong_count,
        total_answers=ts.total_answers,
        last_activity_at=ts.last_activity_at,
      )

    return AnswerResultOut(
      is_correct=result.is_correct,
      correct_key=result.correct_key,
      question=question_out,
      topic_stats=topic_stats_out,
    )

