from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
  __tablename__ = "user"

  id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
  telegram_id: Mapped[int] = mapped_column(
    BigInteger,
    unique=True,
    index=True,
    nullable=False,
  )
  username: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
  first_name: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
  last_name: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
  created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    default=datetime.utcnow,
    nullable=False,
  )
  updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    default=datetime.utcnow,
    onupdate=datetime.utcnow,
    nullable=False,
  )

  question_stats: Mapped[list["UserQuestionStat"]] = relationship(
    back_populates="user",
    cascade="all, delete-orphan",
  )


class Topic(Base):
  __tablename__ = "topic"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  slug: Mapped[str] = mapped_column(String(length=255), unique=True, nullable=False)
  title: Mapped[str] = mapped_column(String(length=255), nullable=False)
  description: Mapped[str | None] = mapped_column(Text, nullable=True)
  is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

  questions: Mapped[list["Question"]] = relationship(
    back_populates="topic",
    cascade="all, delete-orphan",
  )


class Question(Base):
  __tablename__ = "question"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  topic_id: Mapped[int] = mapped_column(
    ForeignKey("topic.id", ondelete="CASCADE"),
    nullable=False,
  )
  text: Mapped[str] = mapped_column(Text, nullable=False)
  options: Mapped[dict[str, str] | None] = mapped_column(JSONB, nullable=True)
  correct_key: Mapped[str | None] = mapped_column(String(length=64), nullable=True)
  difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)
  is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

  topic: Mapped["Topic"] = relationship(back_populates="questions")
  user_stats: Mapped[list["UserQuestionStat"]] = relationship(
    back_populates="question",
    cascade="all, delete-orphan",
  )


class UserQuestionStat(Base):
  __tablename__ = "user_question_stat"

  id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
  user_id: Mapped[int] = mapped_column(
    ForeignKey("user.id", ondelete="CASCADE"),
    nullable=False,
  )
  question_id: Mapped[int] = mapped_column(
    ForeignKey("question.id", ondelete="CASCADE"),
    nullable=False,
  )
  is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
  answered_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    default=datetime.utcnow,
    nullable=False,
  )

  user: Mapped["User"] = relationship(back_populates="question_stats")
  question: Mapped["Question"] = relationship(back_populates="user_stats")

