"""Module for services/application/max handlers/state store."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class QuizSession:
  """Store state for quiz."""
  topic_slug: str
  topic_title: str
  current_question_id: int
  correct: int = 0
  total: int = 0


AI_CHAT_USERS: set[str] = set()
QUIZ_USERS: dict[str, QuizSession] = {}
PATENT_SEARCH_USERS: set[str] = set()
QUIZ_QUESTIONS_PER_SESSION = 3

