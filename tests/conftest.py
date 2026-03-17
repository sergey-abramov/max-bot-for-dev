from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from db.base import Base
from db import models  # noqa: F401  # импортирует модели для регистрации в metadata
from db.config import get_database_url


def _build_engine() -> Engine:
  """
  Строит Engine для тестов.

  По умолчанию использует тот же DATABASE_URL, что и приложение.
  При наличии TEST_DATABASE_URL использует её, чтобы тесты изолированно
  работали с отдельной тестовой БД.
  """
  test_url = os.getenv("TEST_DATABASE_URL")
  if test_url:
    url = test_url
  else:
    url = get_database_url()
  return create_engine(url, future=True)


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
  engine = _build_engine()

  # Полностью пересоздаем схему для чистого состояния тестовой БД.
  Base.metadata.drop_all(bind=engine)
  Base.metadata.create_all(bind=engine)

  try:
    yield engine
  finally:
    # По желанию схему можно удалить после тестов.
    if os.getenv("KEEP_TEST_DB_SCHEMA") != "1":
      Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
  """
  Сессионный объект для тестов.

  Каждый тест выполняется в собственной транзакции, которая откатывается
  по завершении теста.
  """
  connection = engine.connect()
  transaction = connection.begin()

  TestingSessionLocal = sessionmaker(bind=connection, autoflush=False, autocommit=False)
  session = TestingSessionLocal()

  try:
    yield session
  finally:
    session.close()
    transaction.rollback()
    connection.close()

