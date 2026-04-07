from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class RosPatentClientError(Exception):
  """Base exception for RosPatent integration failures."""


class RosPatentAuthError(RosPatentClientError):
  """Raised when RosPatent API key is invalid or missing."""


class RosPatentQueryError(RosPatentClientError):
  """Raised when RosPatent cannot process the provided query."""


class RosPatentUnavailableError(RosPatentClientError):
  """Raised when RosPatent service is temporarily unavailable."""


@dataclass(frozen=True, slots=True)
class RosPatentHit:
  id: str
  title: str
  description: str


class RosPatentApiClient:
  def __init__(
    self,
    api_key: str,
    *,
    base_url: str = "https://searchplatform.rospatent.gov.ru",
    timeout: float = 10.0,
  ) -> None:
    self._api_key = api_key.strip()
    self._base_url = base_url.rstrip("/")
    self._timeout = timeout

  def _headers(self) -> dict[str, str]:
    if not self._api_key:
      return {}
    return {"Authorization": f"Bearer {self._api_key}"}

  def _normalize_hit(self, raw_hit: Any) -> RosPatentHit | None:
    if not isinstance(raw_hit, dict):
      return None

    snippet = raw_hit.get("snippet")
    if not isinstance(snippet, dict):
      return None

    hit_id = str(raw_hit.get("id") or "").strip()
    title = str(snippet.get("title") or "").strip()
    description = str(snippet.get("description") or "").strip()

    if not hit_id and not title and not description:
      return None

    return RosPatentHit(id=hit_id, title=title, description=description)

  async def similar_text_search(self, query: str, *, count: int = 5) -> list[RosPatentHit]:
    url = f"{self._base_url}/patsearch/v0.2/similar_search"
    payload = {
      "type_search": "text_search",
      "pat_text": query,
      "count": count,
    }

    try:
      async with httpx.AsyncClient(timeout=self._timeout) as client:
        response = await client.post(url, json=payload, headers=self._headers())
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
      raise RosPatentUnavailableError("RosPatent service is temporarily unavailable.") from exc

    if response.status_code == 401:
      raise RosPatentAuthError("RosPatent authorization failed.")
    if response.status_code in (400, 500):
      details = self._extract_error_details(response)
      raise RosPatentQueryError(details or "RosPatent query is invalid or ambiguous.")
    if response.status_code >= 500:
      raise RosPatentUnavailableError("RosPatent service returned a server error.")

    try:
      response.raise_for_status()
      data = response.json()
    except (httpx.HTTPStatusError, ValueError) as exc:
      raise RosPatentClientError("Unexpected RosPatent response.") from exc

    hits = data.get("hits") if isinstance(data, dict) else None
    if not isinstance(hits, list):
      return []

    normalized: list[RosPatentHit] = []
    for item in hits:
      normalized_hit = self._normalize_hit(item)
      if normalized_hit is not None:
        normalized.append(normalized_hit)

    return normalized[: max(count, 0)]

  @staticmethod
  def _extract_error_details(response: httpx.Response) -> str:
    try:
      payload = response.json()
    except ValueError:
      return response.text.strip()

    if isinstance(payload, dict):
      # RosPatent error payloads often include `detail` or `message`.
      for key in ("detail", "message", "error"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
          return value.strip()
      return str(payload)

    return str(payload)
