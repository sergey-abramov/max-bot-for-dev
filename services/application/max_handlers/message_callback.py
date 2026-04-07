from __future__ import annotations

import logging
from typing import Any

from db.session import get_session
from services import quiz_service
from services.application.max_handlers.common import extract_callback_payload, extract_user, extract_user_id, send_message, send_text
from services.application.max_handlers.state_store import (
  AI_CHAT_USERS,
  PATENT_SEARCH_USERS,
  QUIZ_QUESTIONS_PER_SESSION,
  QUIZ_USERS,
  QuizSession,
)
from services.integrations.max_api_client import MaxApiClient

logger = logging.getLogger(__name__)


def _build_question_text(question: Any, index: int, total_planned: int) -> str:
  header = f"Вопрос {index + 1} из {total_planned}\n{question.text}\n"
  options = question.options or {}
  rows = [f"{key}. {value}" for key, value in sorted(options.items(), key=lambda item: item[0])]
  return f"{header}\n" + "\n\n".join(rows)


def _build_topic_attachments(topics: list[Any]) -> list[dict[str, Any]]:
  buttons = []
  for topic in topics:
    buttons.append([{"type": "callback", "text": topic.title, "payload": f"victorine:topic:{topic.slug}"}])
  return [{"type": "inline_keyboard", "payload": {"buttons": buttons}}]


def _build_answer_attachments(topic_slug: str, question_id: int, options: dict[str, str] | None) -> list[dict[str, Any]]:
  keys = sorted((options or {}).keys())
  row = [
    {"type": "callback", "text": key, "payload": f"victorine:answer:{topic_slug}:{question_id}:{key}"}
    for key in keys
  ]
  return [{"type": "inline_keyboard", "payload": {"buttons": [row]}}]


async def handle_message_callback(update: dict[str, Any], max_api_client: MaxApiClient) -> None:
  logger.info("MAX webhook: message_callback handled", extra={"update": update})
  payload = extract_callback_payload(update)
  if not payload:
    return

  user_id = extract_user_id(update)
  if not user_id:
    return

  if payload == "menu:hello":
    user = extract_user(update)
    info_lines = [
      "Информация о вас:",
      f"ID: {user.get('user_id', 'неизвестно')}",
      f"Имя: {user.get('name', 'неизвестно')}",
      f"Username: {user.get('username', 'не задан')}",
      f"Роль: {user.get('role', 'неизвестно')}",
    ]
    await send_text(max_api_client, update, "\n".join(info_lines))
    return

  if payload == "menu:chat_ai":
    QUIZ_USERS.pop(user_id, None)
    PATENT_SEARCH_USERS.discard(user_id)
    AI_CHAT_USERS.add(user_id)
    await send_text(max_api_client, update, "Вы в режиме чата с ИИ. Отправьте вопрос текстом.")
    return

  if payload == "menu:patent_search":
    QUIZ_USERS.pop(user_id, None)
    AI_CHAT_USERS.discard(user_id)
    PATENT_SEARCH_USERS.add(user_id)
    await send_text(max_api_client, update, "Введите поисковый запрос")
    return

  if payload == "menu:victorine":
    AI_CHAT_USERS.discard(user_id)
    PATENT_SEARCH_USERS.discard(user_id)
    with get_session() as session:
      topics = quiz_service.list_active_topics(session=session)
      if not topics:
        await send_text(max_api_client, update, "Сейчас нет доступных тем викторины. Попробуйте позже.")
        return
      await send_message(
        max_api_client,
        update,
        text="Запускаем викторину! Выберите тему:",
        attachments=_build_topic_attachments(topics),
      )
    return

  if payload.startswith("victorine:topic:"):
    _, _, topic_slug = payload.split(":", 2)
    with get_session() as session:
      topic = quiz_service.get_topic_by_slug(session=session, slug=topic_slug)
      if topic is None or not topic.is_active:
        await send_text(max_api_client, update, "Выбранная тема недоступна. Попробуйте снова.")
        return
      question = quiz_service.get_random_question_for_topic(session=session, topic_id=topic.id)
      if question is None:
        await send_text(max_api_client, update, "Для этой темы пока нет вопросов.")
        return
      QUIZ_USERS[user_id] = QuizSession(topic_slug=topic.slug, topic_title=topic.title, current_question_id=question.id)
      await send_message(
        max_api_client,
        update,
        text=_build_question_text(question, 0, QUIZ_QUESTIONS_PER_SESSION),
        attachments=_build_answer_attachments(topic.slug, question.id, question.options),
      )
    return

  if not payload.startswith("victorine:answer:"):
    return

  state = QUIZ_USERS.get(user_id)
  if state is None:
    await send_text(max_api_client, update, "Викторина для вас не найдена. Запустите её через /quiz.")
    return

  parts = payload.split(":")
  if len(parts) != 5:
    await send_text(max_api_client, update, "Некорректный формат ответа. Используйте кнопки под вопросом.")
    return

  _, _, topic_slug, question_id_raw, selected_key = parts
  try:
    question_id = int(question_id_raw)
  except ValueError:
    await send_text(max_api_client, update, "Некорректный вопрос. Попробуйте заново.")
    return

  if state.topic_slug != topic_slug or state.current_question_id != question_id:
    await send_text(max_api_client, update, "Этот вопрос уже не актуален. Дождитесь следующего.")
    return

  user = extract_user(update)
  with get_session() as session:
    result = quiz_service.submit_answer(
      session=session,
      telegram_id=int(user_id),
      question_id=question_id,
      selected_key=selected_key,
      username=user.get("username"),
      first_name=user.get("name"),
      last_name=None,
    )

    if result.is_correct:
      state.correct += 1
      await send_text(max_api_client, update, "Верно ✅")
    else:
      await send_text(max_api_client, update, f"Неверно ❌\nПравильный ответ: {result.correct_key}")

    state.total += 1
    if state.total >= QUIZ_QUESTIONS_PER_SESSION:
      await send_text(
        max_api_client,
        update,
        f"Тест по теме «{state.topic_title}» завершён! Ваш результат: {state.correct} из {state.total}.",
      )
      QUIZ_USERS.pop(user_id, None)
      return

    topic = quiz_service.get_topic_by_slug(session=session, slug=state.topic_slug)
    if topic is None:
      await send_text(max_api_client, update, "Тема викторины недоступна. Запустите /quiz заново.")
      QUIZ_USERS.pop(user_id, None)
      return
    next_question = quiz_service.get_random_question_for_topic(session=session, topic_id=topic.id)
    if next_question is None:
      await send_text(max_api_client, update, "Вопросы закончились. Запустите /quiz заново.")
      QUIZ_USERS.pop(user_id, None)
      return
    state.current_question_id = next_question.id
    await send_message(
      max_api_client,
      update,
      text=_build_question_text(next_question, state.total, QUIZ_QUESTIONS_PER_SESSION),
      attachments=_build_answer_attachments(state.topic_slug, next_question.id, next_question.options),
    )
