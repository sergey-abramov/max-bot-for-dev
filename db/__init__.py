"""Module for db/  init  ."""

from .base import Base
from .config import create_engine_from_env, get_database_url, get_engine
from .models import Question, Topic, User, UserQuestionStat
from .repositories.question_repo import (
  get_question_by_id,
  get_questions_by_topic,
  get_random_question_by_topic,
)
from .repositories.stat_repo import TopicStats, get_user_topic_stats, record_user_answer
from .repositories.topic_repo import get_active_topics, get_topic_by_id, get_topic_by_slug
from .repositories.user_repo import (
  get_or_create_user,
  get_user_by_id,
  get_user_by_telegram_id,
)
from .session import SessionLocal, create_session, get_session

__all__ = [
  # Core SQLAlchemy setup
  "Base",
  "get_database_url",
  "create_engine_from_env",
  "get_engine",
  "SessionLocal",
  "create_session",
  "get_session",
  # ORM models
  "User",
  "Topic",
  "Question",
  "UserQuestionStat",
  # User repository
  "get_user_by_telegram_id",
  "get_user_by_id",
  "get_or_create_user",
  # Topic repository
  "get_active_topics",
  "get_topic_by_slug",
  "get_topic_by_id",
  # Question repository
  "get_questions_by_topic",
  "get_random_question_by_topic",
  "get_question_by_id",
  # Stats repository
  "TopicStats",
  "record_user_answer",
  "get_user_topic_stats",
]

