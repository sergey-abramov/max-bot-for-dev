"""Module for db/base."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
  """
  Базовый класс для всех ORM-моделей проекта.

  Пример:

      from sqlalchemy import BigInteger, String
      from sqlalchemy.orm import Mapped, mapped_column, relationship
      from db.base import Base

      class User(Base):
          __tablename__ = "user"

          id: Mapped[int] = mapped_column(primary_key=True)
          telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
          username: Mapped[str | None] = mapped_column(String, nullable=True)
  """

  pass

