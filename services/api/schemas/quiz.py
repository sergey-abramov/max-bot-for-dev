"""Module for services/api/schemas/quiz."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel


class UserSyncPayload(BaseModel):
  """Represent usersyncpayload."""
  telegram_id: int
  username: Optional[str] = None
  first_name: Optional[str] = None
  last_name: Optional[str] = None


class TopicOut(BaseModel):
  """Represent topicout."""
  id: int
  slug: str
  title: str
  description: Optional[str] = None


class QuestionOut(BaseModel):
  """Represent questionout."""
  id: int
  topic_id: int
  topic_slug: str
  text: str
  options: Dict[str, str]
  difficulty: Optional[int] = None


class TopicStatsOut(BaseModel):
  """Represent topicstatsout."""
  topic_id: int
  topic_slug: str
  correct_count: int
  wrong_count: int
  total_answers: int
  last_activity_at: Optional[datetime] = None


class SubmitAnswerPayload(BaseModel):
  """Represent submitanswerpayload."""
  telegram_id: int
  question_id: int
  selected_key: Optional[str] = None
  username: Optional[str] = None
  first_name: Optional[str] = None
  last_name: Optional[str] = None


class AnswerResultOut(BaseModel):
  """Represent answerresultout."""
  is_correct: bool
  correct_key: Optional[str] = None
  question: QuestionOut
  topic_stats: Optional[TopicStatsOut] = None
