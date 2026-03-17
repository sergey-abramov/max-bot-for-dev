from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from .models import Question, Topic
from .session import get_session


TopicSeedData = dict[str, object]
QuestionSeedData = dict[str, object]


TOPICS: list[TopicSeedData] = [
  {
    "slug": "python-basics",
    "title": "Основы Python",
    "description": "Базовые вопросы по синтаксису и ключевым понятиям Python.",
  },
  {
    "slug": "sql-basics",
    "title": "Основы SQL",
    "description": "Вопросы по базовому синтаксису SQL и работе с таблицами.",
  },
  {
    "slug": "java-basics",
    "title": "Основы Java и ООП",
    "description": "Базовые вопросы по ООП и синтаксису Java, используемые в викторине бота.",
  },
]


QUESTIONS: dict[str, list[QuestionSeedData]] = {
  "python-basics": [
    {
      "text": "Какой тип данных возвращает выражение: 1 / 2 в Python 3?",
      "options": {
        "a": "int",
        "b": "float",
        "c": "decimal.Decimal",
        "d": "str",
      },
      "correct_key": "b",
      "difficulty": 1,
    },
    {
      "text": "Как правильно открыть файл для чтения в блоке with?",
      "options": {
        "a": "with open('file.txt'):",
        "b": "with open('file.txt', 'r') as f:",
        "c": "with open('file.txt', 'w') as f:",
        "d": "with open('file.txt', 'rb') as f:",
      },
      "correct_key": "b",
      "difficulty": 1,
    },
    {
      "text": "Что выведет код: print(len({1, 1, 2, 3}))?",
      "options": {
        "a": "4",
        "b": "3",
        "c": "2",
        "d": "Ошибка выполнения",
      },
      "correct_key": "b",
      "difficulty": 1,
    },
  ],
  "sql-basics": [
    {
      "text": "Какой SQL-оператор используется для выборки данных из таблицы?",
      "options": {
        "a": "INSERT",
        "b": "UPDATE",
        "c": "SELECT",
        "d": "DELETE",
      },
      "correct_key": "c",
      "difficulty": 1,
    },
    {
      "text": "Какой оператор используется для фильтрации строк в запросе SELECT?",
      "options": {
        "a": "WHERE",
        "b": "GROUP BY",
        "c": "ORDER BY",
        "d": "LIMIT",
      },
      "correct_key": "a",
      "difficulty": 1,
    },
    {
      "text": "Какой тип связи обычно описывается через внешний ключ (FOREIGN KEY)?",
      "options": {
        "a": "one-to-one",
        "b": "one-to-many / many-to-one",
        "c": "many-to-many",
        "d": "self-reference",
      },
      "correct_key": "b",
      "difficulty": 1,
    },
  ],
  "java-basics": [
    {
      "text": "Что такое ООП?",
      "options": {
        "1": "Объектно-ориентированное программирование — методология программирования, основанная на представлении программы в виде совокупности объектов, каждый из которых является экземпляром определенного класса, а классы образуют иерархию наследования.",
        "2": "Объектно-ориентированное программирование — так называют любой тип программирования, в котором используются понятия высокого уровня и, в отличие от Assembler, в котором не работают напрямую с ячейками памяти ПК.",
        "3": "Объектно-ориентированное программирование — просто красивое понятие. Если вдуматься, оно не несет дополнительной смысловой нагрузки, просто программисты любят аббревиатуры, так области их знаний выглядят сложнее.",
        "4": "Очень одинокий программист.",
      },
      "correct_key": "1",
      "difficulty": 1,
    },
    {
      "text": "Что такое класс в Java?",
      "options": {
        "1": "Уровень сложности программы. Все операторы делятся на классы в зависимости от сложности их использования.",
        "2": "Базовый элемент объектно-ориентирован­ного программирования в языке Java.",
        "3": "Просто одно из возможных названий переменной.",
        "4": "Такое понятие есть только в C++, в Java такого понятия нет.",
      },
      "correct_key": "2",
      "difficulty": 1,
    },
    {
      "text": "Как объявить класс в коде?",
      "options": {
        "1": "class MyClass {}",
        "2": "new class MyClass {}",
        "3": "select * from class MyClass {}",
        "4": "MyClass extends class {}",
      },
      "correct_key": "1",
      "difficulty": 1,
    },
  ],
}


def _get_or_create_topics(session: Session, topics: Iterable[TopicSeedData]) -> dict[str, Topic]:
  """
  Создает недостающие темы и возвращает словарь slug -> Topic.
  """
  existing = (
    session.query(Topic)
    .filter(Topic.slug.in_([t["slug"] for t in topics]))
    .all()
  )
  by_slug: dict[str, Topic] = {t.slug: t for t in existing}

  for data in topics:
    slug = data["slug"]
    if slug in by_slug:
      continue

    topic = Topic(
      slug=slug,  # type: ignore[arg-type]
      title=data["title"],  # type: ignore[arg-type]
      description=data.get("description"),  # type: ignore[arg-type]
      is_active=True,
    )
    session.add(topic)
    by_slug[slug] = topic

  session.flush()
  return by_slug


def _ensure_questions_for_topic(
  session: Session,
  topic: Topic,
  questions: Iterable[QuestionSeedData],
) -> None:
  """
  Создает недостающие вопросы для заданной темы.

  Идентификация вопроса происходит по тексту внутри одной темы.
  """
  existing = (
    session.query(Question)
    .filter(Question.topic_id == topic.id)
    .all()
  )
  existing_by_text = {q.text: q for q in existing}

  for data in questions:
    text = data["text"]
    if text in existing_by_text:
      continue

    question = Question(
      topic_id=topic.id,
      text=text,  # type: ignore[arg-type]
      options=data.get("options"),  # type: ignore[arg-type]
      correct_key=data.get("correct_key"),  # type: ignore[arg-type]
      difficulty=data.get("difficulty"),  # type: ignore[arg-type]
      is_active=True,
    )
    session.add(question)


def seed_initial_data() -> None:
  """
  Основная точка входа для сидинга.

  Скрипт является идемпотентным: повторный запуск не создаст дубликатов
  тем и вопросов (сравнение по slug для тем и по text внутри темы для вопросов).
  """
  with get_session() as session:
    topics_by_slug = _get_or_create_topics(session, TOPICS)

    for slug, questions in QUESTIONS.items():
      topic = topics_by_slug.get(slug)
      if topic is None:
        # Если по какой-то причине темы нет (например, не добавлена в TOPICS),
        # пропускаем такие вопросы.
        continue
      _ensure_questions_for_topic(session, topic, questions)


if __name__ == "__main__":
  seed_initial_data()

