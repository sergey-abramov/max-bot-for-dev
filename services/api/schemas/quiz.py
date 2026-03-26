from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel


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
