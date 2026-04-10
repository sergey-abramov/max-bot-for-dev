"""Module for db/config."""

import os
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from dotenv import load_dotenv


# Автоматически подхватываем .env при работе из локального Python-окружения.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def get_database_url(default: Optional[str] = None) -> str:
  """
  Возвращает URL подключения к базе данных.

  Приоритет:
  1. LOCAL_DATABASE_URL — удобно для локальной разработки с host=localhost;
  2. DATABASE_URL — используется в Docker и может ссылаться на host=db;
  3. default (если передан).

  Ожидаемый формат: postgresql+psycopg://user:password@host:port/dbname
  """
  url = os.getenv("LOCAL_DATABASE_URL") or os.getenv("DATABASE_URL", default)
  if not url:
    raise RuntimeError(
      "DATABASE_URL/LOCAL_DATABASE_URL is not set. "
      "Укажите строку подключения к PostgreSQL в переменных окружения "
      "DATABASE_URL или LOCAL_DATABASE_URL, либо передайте default."
    )
  return _normalize_sqlalchemy_url(url)


def _normalize_sqlalchemy_url(url: str) -> str:
  """
  Нормализует URL для SQLAlchemy.

  Поддерживает входной формат postgres://..., который часто отдают
  managed-провайдеры, и приводит его к postgresql+psycopg://...
  """
  normalized = url.strip()
  if normalized.startswith("postgresql+psycopg://"):
    return normalized
  if normalized.startswith("postgresql://"):
    return "postgresql+psycopg://" + normalized[len("postgresql://") :]
  if normalized.startswith("postgres://"):
    return "postgresql+psycopg://" + normalized[len("postgres://") :]
  return normalized


def create_engine_from_env(
  *, echo: bool = False, future: bool = True
) -> Engine:
  """
  Создает экземпляр Engine на основе DATABASE_URL.
  """
  url = get_database_url()
  return create_engine(url, echo=echo, future=future)


_engine: Optional[Engine] = None


def get_engine() -> Engine:
  """
  Ленивая инициализация и возврат singleton Engine.
  """
  global _engine
  if _engine is None:
    _engine = create_engine_from_env()
  return _engine

