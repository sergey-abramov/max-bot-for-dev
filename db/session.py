from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session, sessionmaker

from .config import get_engine


SessionLocal = sessionmaker(
  bind=get_engine(),
  autocommit=False,
  autoflush=False,
)


def create_session() -> Session:
  """
  Создает новый объект Session.
  """
  return SessionLocal()


@contextmanager
def get_session() -> Iterator[Session]:
  """
  Контекстный менеджер для безопасной работы с сессией.

  Пример:

      with get_session() as session:
          # work with session
          ...
  """
  session = create_session()
  try:
    yield session
    session.commit()
  except Exception:
    session.rollback()
    raise
  finally:
    session.close()

