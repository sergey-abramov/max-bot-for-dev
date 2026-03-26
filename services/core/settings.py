from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
  max_webhook_path: str = "https://platform-api.max.ru/subscriptions"
  max_bot_token: str = ""
  max_bot_mode: str = "webhook"
  database_url: str = ""
  test_database_url: str = ""
  quiz_api_url: str = ""
  stt_api_url: str = ""
  max_stt_enabled: bool = False
  app_env: str = "development"

  def is_production(self) -> bool:
    return self.app_env == "production"

  def validate_webhook_runtime(self) -> None:
    if self.max_bot_mode != "webhook":
      raise ValueError(
        f"Unsupported MAX_BOT_MODE={self.max_bot_mode!r}. "
        "Only webhook mode is allowed for this runtime."
      )


def get_settings() -> Settings:
  app_env = (
    os.getenv("APP_ENV")
    or os.getenv("VERCEL_ENV")
    or os.getenv("NODE_ENV")
    or "development"
  ).strip().lower()

  return Settings(
    max_webhook_path=os.getenv("MAX_WEBHOOK_PATH", "https://platform-api.max.ru/subscriptions").strip(),
    max_bot_token=os.getenv("MAX_BOT_TOKEN", "").strip(),
    max_bot_mode=os.getenv("MAX_BOT_MODE", "webhook").strip().lower(),
    database_url=os.getenv("DATABASE_URL", "").strip(),
    test_database_url=os.getenv("TEST_DATABASE_URL", "").strip(),
    quiz_api_url=os.getenv("QUIZ_API_URL", "").strip(),
    stt_api_url=os.getenv("STT_API_URL", "").strip(),
    max_stt_enabled=(os.getenv("MAX_STT_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")),
    app_env=app_env,
  )
