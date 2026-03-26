# Deploy на Vercel

Этот гайд адаптирован под текущую структуру проекта:
- Python API-рантайм через `api/index.py`;
- маршрутизация в `vercel.json`;
- webhook endpoint по пути `/webhooks/max`.

## 1) Что должно быть готово заранее

- Аккаунт Vercel и доступ к проекту.
- Токен бота Max (`MAX_BOT_TOKEN`).
- Рабочая PostgreSQL-база (`DATABASE_URL`).
- Ключ OpenRouter (`OPENROUTER_API_KEY`), если нужен AI-чат.

Важно:
- В production используйте только `MAX_BOT_MODE=webhook`.
- Внешняя платформа Max должна отправлять webhook в ваш публичный URL.

## 2) Локальная подготовка проекта

```bash
cp .env.example .env
```

Заполните обязательные переменные в `.env`:

- `MAX_BOT_TOKEN`
- `DATABASE_URL`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL` (можно оставить дефолт)
- `MAX_BOT_MODE=webhook`

Рекомендуемые значения:

- `MAX_WEBHOOK_PATH=/webhooks/max`
- `APP_ENV=development` (локально)

## 3) Проверка API локально перед деплоем

Запуск:

```bash
uvicorn services.quiz_api:app --reload
```

Быстрая проверка:

- откройте `http://127.0.0.1:8000/docs`;
- убедитесь, что доступны endpoints викторины;
- проверьте, что POST на `http://127.0.0.1:8000/webhooks/max` отрабатывает без ошибок формата.

## 4) Деплой через Vercel CLI

Установите и авторизуйтесь:

```bash
npm i -g vercel
vercel login
```

Свяжите репозиторий с проектом:

```bash
vercel link
```

Создайте preview-деплой:

```bash
vercel deploy
```

Выкатите production:

```bash
vercel --prod
```

## 5) Переменные окружения в Vercel

В Project Settings -> Environment Variables задайте (минимум):

- `MAX_BOT_TOKEN`
- `DATABASE_URL`
- `MAX_WEBHOOK_PATH` = `/webhooks/max`
- `MAX_BOT_MODE` = `webhook`
- `APP_ENV` = `production`

Опционально:

- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `MAX_STT_ENABLED`
- `STT_API_URL`
- `STT_MODEL`
- `QUIZ_API_URL` (обычно URL вашего деплоя)

После изменения env-переменных делайте redeploy.

## 6) Настройка webhook во внешней платформе

После production-деплоя получите URL вида:

`https://<your-project>.vercel.app`

Укажите webhook URL:

`https://<your-project>.vercel.app/webhooks/max`

## 7) Проверка после релиза

Минимальный smoke-check:

1. Отправьте тестовый webhook update.
2. Убедитесь, что endpoint отвечает `200` и `{"ok": true}`.
3. Проверьте, что `/docs` и `/openapi.json` открываются.

Проверка CLI-логов:

```bash
vercel logs <deployment-url>
```

## 8) Типичные проблемы

### 500 Webhook dispatch failed

- Проблема в обработчике события или внешнем API.
- Смотрите runtime-логи Vercel.

### Ошибка запуска Python на деплое

- Проверьте валидность `pyproject.toml`.
- Убедитесь, что `vercel.json` ссылается на `api/index.py`.

### Проблемы с БД

- Неверный `DATABASE_URL`.
- Для managed Postgres обычно нужен `sslmode=require`.

## 9) Что в проекте уже настроено

- `api/index.py` экспортирует ASGI-приложение.
- `vercel.json` перенаправляет:
  - `/webhooks/max`
  - `/users/sync`
  - `/topics`
  - `/topics/:slug/random-question`
  - `/answers/submit`
  - `/docs`, `/redoc`, `/openapi.json`
- В production рантайм валидирует режим webhook.
