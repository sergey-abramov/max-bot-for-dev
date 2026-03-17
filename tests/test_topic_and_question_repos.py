from __future__ import annotations

from db.repositories.question_repo import (
  get_question_by_id,
  get_questions_by_topic,
  get_random_question_by_topic,
)
from db.repositories.topic_repo import (
  get_active_topics,
  get_topic_by_id,
  get_topic_by_slug,
)
from db.seed import seed_initial_data


def test_get_active_topics_and_by_slug(db_session) -> None:
  seed_initial_data()

  topics = get_active_topics(db_session)
  assert topics, "ожидается хотя бы одна активная тема после сидинга"

  slugs = {t.slug for t in topics}
  assert "python-basics" in slugs
  assert "sql-basics" in slugs

  topic = get_topic_by_slug(db_session, "python-basics")
  assert topic is not None

  same_topic = get_topic_by_id(db_session, topic.id)
  assert same_topic is not None
  assert same_topic.slug == "python-basics"


def test_questions_by_topic_and_random_question(db_session) -> None:
  seed_initial_data()

  topic = get_topic_by_slug(db_session, "python-basics")
  assert topic is not None

  questions = get_questions_by_topic(db_session, topic.id)
  assert questions, "ожидаются вопросы по теме python-basics после сидинга"

  for q in questions:
    assert q.topic_id == topic.id
    assert q.is_active is True

  first = questions[0]
  fetched = get_question_by_id(db_session, first.id)
  assert fetched is not None
  assert fetched.id == first.id

  random_q = get_random_question_by_topic(db_session, topic.id)
  assert random_q is not None
  assert random_q.topic_id == topic.id
  assert random_q.is_active is True

