import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def get_database_url(default: Optional[str] = None) -> str:
  """
  Возвращает URL подключения к базе данных из переменной окружения DATABASE_URL.

  Ожидаемый формат: postgresql+psycopg://user:password@host:port/dbname
  """
  url = os.getenv("DATABASE_URL", default)
  if not url:
    raise RuntimeError(
      "DATABASE_URL is not set. "
      "Укажите строку подключения к PostgreSQL в переменной окружения DATABASE_URL."
    )
  return url


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

