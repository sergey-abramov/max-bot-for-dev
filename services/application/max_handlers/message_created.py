from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import quote_plus

import httpx
from db.session import get_session
from services import quiz_service
from services.application.max_handlers.common import (
  dump_identity,
  extract_message_text,
  extract_user,
  extract_user_id,
  send_message,
  send_text,
)
from services.application.max_handlers.state_store import (
  AI_CHAT_USERS,
  PATENT_SEARCH_USERS,
  QUIZ_QUESTIONS_PER_SESSION,
  QUIZ_USERS,
  QuizSession,
)
from services.core.settings import get_settings

from services.integrations.max_api_client import MaxApiClient
from services.integrations.rospatent_api_client import (
  RosPatentApiClient,
  RosPatentAuthError,
  RosPatentClientError,
  RosPatentQueryError,
  RosPatentUnavailableError,
)

logger = logging.getLogger(__name__)


def _build_start_menu() -> str:
  return "Добро пожаловать! Выберите действие:"


def _build_main_menu_attachments() -> list[dict[str, Any]]:
  return [
    {
      "type": "inline_keyboard",
      "payload": {
        "buttons": [
          [
            {"type": "callback", "text": "ℹ️ Информация обо мне", "payload": "menu:hello"},
            {"type": "callback", "text": "📝 Викторина по Java", "payload": "menu:victorine"},
          ],
          [
            {"type": "callback", "text": "🤖 Чат с ИИ", "payload": "menu:chat_ai"},
            {"type": "callback", "text": "🔎 Поиск патентов", "payload": "menu:patent_search"},
          ],
        ]
      },
    }
  ]


def _normalize_query(text: str) -> str:
  return " ".join((text or "").split()).strip()


def _is_valid_patent_query(text: str) -> bool:
  normalized = _normalize_query(text)
  if len(normalized) < 3:
    return False
  if not any(char.isalpha() for char in normalized):
    return False
  meaningful = [char.lower() for char in normalized if char.isalnum()]
  if len(meaningful) < 3:
    return False
  if len(set(meaningful)) < 3:
    return False
  if re.fullmatch(r"[\W_]+", normalized):
    return False
  return True


def _truncate(value: str, *, max_len: int = 300) -> str:
  text = _normalize_query(value)
  if len(text) <= max_len:
    return text
  return f"{text[: max_len - 1].rstrip()}…"


def _build_patent_public_url(patent_id: str) -> str:
  return f"https://searchplatform.rospatent.gov.ru/patsearch?query={quote_plus(patent_id)}"


def _build_patent_attachments(patent_id: str) -> list[dict[str, Any]]:
  return [
    {
      "type": "inline_keyboard",
      "payload": {
        "buttons": [[{"type": "link", "text": "Открыть патент", "url": _build_patent_public_url(patent_id)}]]
      },
    }
  ]


async def _send_main_menu(update: dict[str, Any], max_api_client: MaxApiClient) -> None:
  await send_message(
    max_api_client,
    update,
    text=_build_start_menu(),
    attachments=_build_main_menu_attachments(),
  )


def _build_question_text(question: Any, index: int, total_planned: int) -> str:
  header = f"Вопрос {index + 1} из {total_planned}\n{question.text}\n"
  options = question.options or {}
  rows = [f"{key}. {value}" for key, value in sorted(options.items(), key=lambda item: item[0])]
  return f"{header}\n" + "\n\n".join(rows)


async def _call_openrouter(question: str, api_key: str, model: str) -> str:
  if not api_key:
    return "OPENROUTER_API_KEY не настроен."
  async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.post(
      "https://openrouter.ai/api/v1/chat/completions",
      headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
      json={
        "model": model,
        "messages": [
          {"role": "system", "content": "Ты дружелюбный русскоязычный ассистент. Отвечай кратко и по делу."},
          {"role": "user", "content": question},
        ],
      },
    )
    response.raise_for_status()
    data = response.json()
    return str((data.get("choices") or [{}])[0].get("message", {}).get("content") or "").strip() or "Не удалось получить ответ от модели."


async def _start_quiz(update: dict[str, Any], max_api_client: MaxApiClient, user_id: str) -> None:
  with get_session() as session:
    topics = quiz_service.list_active_topics(session=session)
    if not topics:
      await send_text(max_api_client, update, "Сейчас нет доступных тем викторины. Попробуйте позже.")
      return
    default_topic = topics[0]
    question = quiz_service.get_random_question_for_topic(session=session, topic_id=default_topic.id)
    if question is None:
      await send_text(max_api_client, update, "Для выбранной темы нет вопросов.")
      return
    QUIZ_USERS[user_id] = QuizSession(
      topic_slug=default_topic.slug,
      topic_title=default_topic.title,
      current_question_id=question.id,
    )
    await send_text(
      max_api_client,
      update,
      f"Запускаем викторину по теме «{default_topic.title}».\n\n{_build_question_text(question, 0, QUIZ_QUESTIONS_PER_SESSION)}",
    )


async def handle_message_created(update: dict[str, Any], max_api_client: MaxApiClient) -> None:
  logger.info("MAX webhook: message_created handled", extra={"update": update})

  text = extract_message_text(update)
  user_id = extract_user_id(update)
  if not user_id:
    logger.warning("MAX webhook: message received but user_id missing", extra={"update": update})

  if user_id and text.startswith("/"):
    AI_CHAT_USERS.discard(user_id)
    PATENT_SEARCH_USERS.discard(user_id)

  if text == "/start":
    await send_message(
      max_api_client,
      update,
      text=_build_start_menu(),
      attachments=_build_main_menu_attachments(),
    )
    return

  if text == "/info":
    user = extract_user(update)
    await send_text(
      max_api_client,
      update,
      "\n".join(
        [
          "Информация о вас:",
          f"ID: {user.get('user_id', 'неизвестно')}",
          f"Имя: {user.get('name', 'неизвестно')}",
          f"Username: {user.get('username', 'не задан')}",
          f"Роль: {user.get('role', 'неизвестно')}",
        ]
      ),
    )
    return

  if text in ("/whoami", "/debug_user"):
    await send_text(max_api_client, update, dump_identity(update))
    return

  if text == "/quiz":
    if not user_id:
      await send_text(max_api_client, update, "Не удалось определить пользователя для викторины.")
      return
    await _start_quiz(update, max_api_client, user_id)
    return

  if text == "/ai":
    if not user_id:
      await send_text(max_api_client, update, "Не удалось определить пользователя для режима ИИ.")
      return
    QUIZ_USERS.pop(user_id, None)
    PATENT_SEARCH_USERS.discard(user_id)
    AI_CHAT_USERS.add(user_id)
    await send_text(max_api_client, update, "Режим чата с ИИ включен. Отправьте ваш вопрос.")
    return

  if text == "/stop":
    if user_id:
      AI_CHAT_USERS.discard(user_id)
      QUIZ_USERS.pop(user_id, None)
      PATENT_SEARCH_USERS.discard(user_id)
    await send_text(max_api_client, update, "Режимы сброшены. Напишите /start.")
    return

  quiz = QUIZ_USERS.get(user_id) if user_id else None
  if quiz is not None:
    selected_key = text.strip().upper()
    with get_session() as session:
      user = extract_user(update)
      result = quiz_service.submit_answer(
        session=session,
        telegram_id=int(user_id),
        question_id=quiz.current_question_id,
        selected_key=selected_key,
        username=user.get("username"),
        first_name=user.get("name"),
        last_name=None,
      )
      if result.is_correct:
        quiz.correct += 1
        await send_text(max_api_client, update, "Верно ✅")
      else:
        await send_text(max_api_client, update, f"Неверно ❌\nПравильный ответ: {result.correct_key}")
      quiz.total += 1
      if quiz.total >= QUIZ_QUESTIONS_PER_SESSION:
        await send_text(
          max_api_client,
          update,
          f"Тест по теме «{quiz.topic_title}» завершён! Ваш результат: {quiz.correct} из {quiz.total}.",
        )
        QUIZ_USERS.pop(user_id, None)
        return
      topic = quiz_service.get_topic_by_slug(session=session, slug=quiz.topic_slug)
      if topic is None:
        await send_text(max_api_client, update, "Тема викторины недоступна. Запустите /quiz заново.")
        QUIZ_USERS.pop(user_id, None)
        return
      question = quiz_service.get_random_question_for_topic(session=session, topic_id=topic.id)
      if question is None:
        await send_text(max_api_client, update, "Вопросы закончились. Запустите /quiz заново.")
        QUIZ_USERS.pop(user_id, None)
        return
      quiz.current_question_id = question.id
      await send_text(max_api_client, update, _build_question_text(question, quiz.total, QUIZ_QUESTIONS_PER_SESSION))
    return

  if user_id and user_id in AI_CHAT_USERS:
    try:
      resolved = get_settings()
      answer = await _call_openrouter(text, resolved.openrouter_api_key, resolved.openrouter_model)
      await send_text(max_api_client, update, answer)
    except Exception:
      logger.exception("MAX webhook: ai response failed")
      await send_text(max_api_client, update, "Не удалось получить ответ от ИИ. Попробуйте позже.")
    return

  if user_id and user_id in PATENT_SEARCH_USERS:
    PATENT_SEARCH_USERS.discard(user_id)
    query = _normalize_query(text)
    if not _is_valid_patent_query(query):
      await send_text(
        max_api_client,
        update,
        "Уточните запрос (например, добавьте дату, город, отрасль, ключевые слова).",
      )
      await _send_main_menu(update, max_api_client)
      return

    try:
      settings = get_settings()
      client = RosPatentApiClient(settings.rospatent_api_key)
      hits = await client.similar_text_search(query, count=5)
    except RosPatentAuthError:
      await send_text(
        max_api_client,
        update,
        "Сервис поиска патентов временно недоступен: проблема с API ключом.",
      )
      await _send_main_menu(update, max_api_client)
      return
    except RosPatentQueryError:
      await send_text(
        max_api_client,
        update,
        "Не удалось обработать запрос. Попробуйте уточнить формулировку.",
      )
      await _send_main_menu(update, max_api_client)
      return
    except RosPatentUnavailableError:
      await send_text(max_api_client, update, "Сервис временно недоступен. Попробуйте позже.")
      await _send_main_menu(update, max_api_client)
      return
    except RosPatentClientError:
      logger.exception("MAX webhook: RosPatent integration failed")
      await send_text(max_api_client, update, "Не удалось выполнить поиск патентов. Попробуйте позже.")
      await _send_main_menu(update, max_api_client)
      return
    except Exception:
      logger.exception("MAX webhook: unexpected RosPatent failure")
      await send_text(max_api_client, update, "Не удалось выполнить поиск патентов. Попробуйте позже.")
      await _send_main_menu(update, max_api_client)
      return

    if not hits:
      await send_text(max_api_client, update, "Ничего не найдено. Попробуйте переформулировать запрос.")
      await _send_main_menu(update, max_api_client)
      return

    for idx, hit in enumerate(hits[:5], start=1):
      title = _truncate(hit.title or f"Патент #{hit.id}", max_len=120)
      description = _truncate(hit.description or "Описание отсутствует.", max_len=300)
      await send_message(
        max_api_client,
        update,
        text=f"{idx}. {title}\n\n{description}",
        attachments=_build_patent_attachments(hit.id),
      )

    await _send_main_menu(update, max_api_client)
    return

  await _send_main_menu(update, max_api_client)
