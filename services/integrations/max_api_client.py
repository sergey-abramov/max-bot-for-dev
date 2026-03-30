from __future__ import annotations

import httpx


class MaxApiClient:
  def __init__(self, bot_token: str, base_url: str = "https://platform-api.max.ru") -> None:
    self._bot_token = bot_token
    self._base_url = base_url.rstrip("/")

  def _headers(self) -> dict[str, str]:
    return {"Authorization": f"Bearer {self._bot_token}"} if self._bot_token else {}

  async def post(self, path: str, payload: dict) -> dict:
    url = f"{self._base_url}/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=10.0) as client:
      response = await client.post(url, json=payload, headers=self._headers())
      response.raise_for_status()
      return response.json()

  async def get(self, path: str) -> dict:
    url = f"{self._base_url}/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=10.0) as client:
      response = await client.get(url, headers=self._headers())
      response.raise_for_status()
      return response.json()

  async def list_subscriptions(self) -> list[dict]:
    payload = await self.get("/subscriptions")
    subscriptions = payload.get("subscriptions")
    return subscriptions if isinstance(subscriptions, list) else []

  async def create_subscription(self, *, url: str, update_types: list[str] | None = None) -> dict:
    body: dict[str, object] = {"url": url}
    if update_types:
      body["update_types"] = update_types
    return await self.post("/subscriptions", body)

  async def ensure_webhook_subscription(
    self,
    *,
    url: str,
    update_types: list[str] | None = None,
  ) -> dict:
    subscriptions = await self.list_subscriptions()
    for item in subscriptions:
      if str(item.get("url") or "").strip() == url:
        return {"ok": True, "status": "exists", "url": url}
    result = await self.create_subscription(url=url, update_types=update_types)
    return {"ok": True, "status": "created", "url": url, "result": result}
