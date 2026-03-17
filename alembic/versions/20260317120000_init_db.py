"""Initial database schema for quiz bot.

Revision ID: 20260317120000_init_db
Revises: 
Create Date: 2026-03-17 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260317120000_init_db"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
  op.create_table(
    "user",
    sa.Column("id", sa.BigInteger(), primary_key=True, nullable=False),
    sa.Column("telegram_id", sa.BigInteger(), nullable=False),
    sa.Column("username", sa.String(length=255), nullable=True),
    sa.Column("first_name", sa.String(length=255), nullable=True),
    sa.Column("last_name", sa.String(length=255), nullable=True),
    sa.Column(
      "created_at",
      sa.DateTime(timezone=True),
      nullable=False,
    ),
    sa.Column(
      "updated_at",
      sa.DateTime(timezone=True),
      nullable=False,
    ),
    sa.UniqueConstraint("telegram_id", name="uq_user_telegram_id"),
  )
  op.create_index(
    "ix_user_telegram_id",
    "user",
    ["telegram_id"],
    unique=False,
  )

  op.create_table(
    "topic",
    sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
    sa.Column("slug", sa.String(length=255), nullable=False),
    sa.Column("title", sa.String(length=255), nullable=False),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column(
      "is_active",
      sa.Boolean(),
      nullable=False,
      server_default=sa.text("true"),
    ),
    sa.UniqueConstraint("slug", name="uq_topic_slug"),
  )

  op.create_table(
    "question",
    sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
    sa.Column("topic_id", sa.Integer(), nullable=False),
    sa.Column("text", sa.Text(), nullable=False),
    sa.Column(
      "options",
      postgresql.JSONB(astext_type=sa.Text()),
      nullable=True,
    ),
    sa.Column("correct_key", sa.String(length=64), nullable=True),
    sa.Column("difficulty", sa.Integer(), nullable=True),
    sa.Column(
      "is_active",
      sa.Boolean(),
      nullable=False,
      server_default=sa.text("true"),
    ),
    sa.ForeignKeyConstraint(
      ["topic_id"],
      ["topic.id"],
      name="fk_question_topic_id_topic",
      ondelete="CASCADE",
    ),
  )

  op.create_table(
    "user_question_stat",
    sa.Column("id", sa.BigInteger(), primary_key=True, nullable=False),
    sa.Column("user_id", sa.BigInteger(), nullable=False),
    sa.Column("question_id", sa.Integer(), nullable=False),
    sa.Column("is_correct", sa.Boolean(), nullable=False),
    sa.Column(
      "answered_at",
      sa.DateTime(timezone=True),
      nullable=False,
    ),
    sa.ForeignKeyConstraint(
      ["user_id"],
      ["user.id"],
      name="fk_user_question_stat_user_id_user",
      ondelete="CASCADE",
    ),
    sa.ForeignKeyConstraint(
      ["question_id"],
      ["question.id"],
      name="fk_user_question_stat_question_id_question",
      ondelete="CASCADE",
    ),
  )


def downgrade() -> None:
  op.drop_table("user_question_stat")
  op.drop_table("question")
  op.drop_table("topic")
  op.drop_index("ix_user_telegram_id", table_name="user")
  op.drop_table("user")

