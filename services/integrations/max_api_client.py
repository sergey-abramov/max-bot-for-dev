from __future__ import annotations

import httpx


class MaxApiClient:
  def __init__(self, bot_token: str, base_url: str = "https://api.max.ru") -> None:
    self._bot_token = bot_token
    self._base_url = base_url.rstrip("/")

  async def post(self, path: str, payload: dict) -> dict:
    headers = {"Authorization": f"Bearer {self._bot_token}"} if self._bot_token else {}
    url = f"{self._base_url}/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=10.0) as client:
      response = await client.post(url, json=payload, headers=headers)
      response.raise_for_status()
      return response.json()
