from __future__ import annotations

from db.repositories.question_repo import get_questions_by_topic
from db.repositories.stat_repo import get_user_topic_stats, record_user_answer
from db.repositories.topic_repo import get_topic_by_slug
from db.repositories.user_repo import get_or_create_user
from db.seed import seed_initial_data


def test_record_user_answer_and_topic_stats(db_session) -> None:
  seed_initial_data()

  user = get_or_create_user(
    session=db_session,
    telegram_id=111222333,
    username="stats_user",
  )

  topic = get_topic_by_slug(db_session, "sql-basics")
  assert topic is not None

  questions = get_questions_by_topic(db_session, topic.id, limit=2)
  assert len(questions) >= 2

  q1, q2 = questions[:2]

  record_user_answer(
    session=db_session,
    user_id=user.id,
    question_id=q1.id,
    is_correct=True,
  )
  record_user_answer(
    session=db_session,
    user_id=user.id,
    question_id=q2.id,
    is_correct=False,
  )

  stats = get_user_topic_stats(
    session=db_session,
    user_id=user.id,
    topic_id=topic.id,
  )

  assert stats is not None
  assert stats.topic.id == topic.id
  assert stats.correct_count == 1
  assert stats.wrong_count == 1
  assert stats.total_answers == 2
  assert stats.last_activity_at is not None

