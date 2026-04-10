"""Module for services/core/settings."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
  """Represent settings."""
  max_webhook_path: str = "/webhooks/max"
  public_base_url: str = ""
  max_webhook_autosubscribe: bool = False
  max_bot_token: str = ""
  max_bot_mode: str = "webhook"
  database_url: str = ""
  test_database_url: str = ""
  quiz_api_url: str = ""
  rospatent_api_key: str = ""
  openrouter_api_key: str = ""
  openrouter_model: str = "qwen/qwen-2.5-7b-instruct"
  stt_api_url: str = ""
  max_stt_enabled: bool = False
  app_env: str = "development"

  def is_production(self) -> bool:
    """Return whether is production."""
    return self.app_env == "production"

  def validate_webhook_runtime(self) -> None:
    """Validate webhook runtime."""
    if self.max_bot_mode != "webhook":
      raise ValueError(
        f"Unsupported MAX_BOT_MODE={self.max_bot_mode!r}. "
        "Only webhook mode is allowed for this runtime."
      )

  def webhook_public_url(self) -> str:
    """Perform webhook public url."""
    base = self.public_base_url.strip().rstrip("/")
    if not base:
      return ""
    return f"{base}{self.max_webhook_path}"


def get_settings() -> Settings:
  """Return settings."""
  app_env = (
    os.getenv("APP_ENV")
    or os.getenv("VERCEL_ENV")
    or os.getenv("NODE_ENV")
    or "development"
  ).strip().lower()

  raw_webhook_path = os.getenv("MAX_WEBHOOK_PATH", "/webhooks/max").strip()
  max_webhook_path = raw_webhook_path if raw_webhook_path.startswith("/") else f"/{raw_webhook_path.lstrip('/')}"
  public_base_url = os.getenv("PUBLIC_BASE_URL", "").strip()
  max_webhook_autosubscribe = os.getenv("MAX_WEBHOOK_AUTOSUBSCRIBE", "false").strip().lower() in ("1", "true", "yes", "on")

  return Settings(
    max_webhook_path=max_webhook_path,
    public_base_url=public_base_url,
    max_webhook_autosubscribe=max_webhook_autosubscribe,
    max_bot_token=os.getenv("MAX_BOT_TOKEN", "").strip(),
    max_bot_mode=os.getenv("MAX_BOT_MODE", "webhook").strip().lower(),
    database_url=os.getenv("DATABASE_URL", "").strip(),
    test_database_url=os.getenv("TEST_DATABASE_URL", "").strip(),
    quiz_api_url=os.getenv("QUIZ_API_URL", "").strip(),
    rospatent_api_key=os.getenv("ROSPATENT_API_KEY", "").strip(),
    openrouter_api_key=os.getenv("OPENROUTER_API_KEY", "").strip(),
    openrouter_model=os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-7b-instruct").strip(),
    stt_api_url=os.getenv("STT_API_URL", "").strip(),
    max_stt_enabled=(os.getenv("MAX_STT_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")),
    app_env=app_env,
  )
