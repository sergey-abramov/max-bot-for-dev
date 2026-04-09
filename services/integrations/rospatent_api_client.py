from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


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
  document: str
  publication_date: str
  applicant: str
  author: str
  ipc: str


class RosPatentApiClient:
  def __init__(
    self,
    api_key: str,
    *,
    base_url: str = "https://searchplatform.rospatent.gov.ru",
    timeout: float = 120.0,
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
    biblio = raw_hit.get("biblio")
    biblio_ru = biblio.get("ru", {}) if isinstance(biblio, dict) else {}
    title = self._normalize_markup_text(str(snippet.get("title") or biblio_ru.get("title") or "").strip())
    description = self._normalize_markup_text(str(snippet.get("description") or "").strip())
    document = self._extract_document_info(raw_hit, biblio_ru, hit_id)
    publication_date = self._extract_text_field(
      biblio_ru,
      (
        "publication_date",
        "publishing_date",
        "published_at",
        "date_publish",
        "pub_date",
        "date",
      ),
    )
    applicant = self._extract_text_field(biblio_ru, ("applicant", "applicants", "holder", "holders"))
    author = self._extract_text_field(biblio_ru, ("author", "authors", "inventor", "inventors"))
    ipc = self._extract_text_field(biblio_ru, ("ipc", "ipc_index", "mki", "mpk", "classification"))

    if not hit_id and not title and not description:
      return None

    return RosPatentHit(
      id=hit_id,
      title=title,
      description=description,
      document=document,
      publication_date=publication_date,
      applicant=applicant,
      author=author,
      ipc=ipc,
    )

  async def similar_text_search(self, query: str, *, count: int = 5) -> list[RosPatentHit]:
    url = f"{self._base_url}/patsearch/v0.2/search"
    safe_count = max(int(count), 0)
    payload = {
      "qn": query,
      "limit": safe_count,
      "offset": 0,
    }
    logger.info("RosPatent integration request: method=POST url=%s body=%s", url, payload)

    try:
      async with httpx.AsyncClient(timeout=self._timeout) as client:
        response = await client.post(url, json=payload, headers=self._headers())
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
      raise RosPatentUnavailableError("RosPatent service is temporarily unavailable.") from exc

    if response.status_code == 401:
      raise RosPatentAuthError("RosPatent authorization failed.")
    if response.status_code in (400, 500):
      details = self._extract_error_details(response)
      logger.error("RosPatent integration error: method=POST url=%s status=%s body=%s", url, response.status_code, details)
      raise RosPatentQueryError(details or "RosPatent query is invalid or ambiguous.")
    if response.status_code >= 500:
      details = self._extract_error_details(response)
      logger.error("RosPatent integration error: method=POST url=%s status=%s body=%s", url, response.status_code, details)
      raise RosPatentUnavailableError("RosPatent service returned a server error.")

    try:
      response.raise_for_status()
      data = response.json()
    except (httpx.HTTPStatusError, ValueError) as exc:
      raise RosPatentClientError("Unexpected RosPatent response.") from exc
    logger.info(
      "RosPatent integration response: method=POST url=%s status=%s body=%s",
      url,
      response.status_code,
      data,
    )

    hits = data.get("hits") if isinstance(data, dict) else None
    if not isinstance(hits, list):
      return []
    self._log_hit_schema(hits)

    normalized: list[RosPatentHit] = []
    for item in hits:
      normalized_hit = self._normalize_hit(item)
      if normalized_hit is not None:
        normalized.append(normalized_hit)

    return normalized[:safe_count]

  def _log_hit_schema(self, hits: list[Any]) -> None:
    sample_limit = 2
    for idx, hit in enumerate(hits[:sample_limit], start=1):
      if not isinstance(hit, dict):
        logger.info("RosPatent hit schema sample #%s: non-dict hit type=%s", idx, type(hit).__name__)
        continue

      biblio = hit.get("biblio")
      biblio_ru = biblio.get("ru", {}) if isinstance(biblio, dict) and isinstance(biblio.get("ru"), dict) else {}
      snippet = hit.get("snippet")
      snippet_dict = snippet if isinstance(snippet, dict) else {}

      logger.info(
        "RosPatent hit schema sample #%s: top_keys=%s biblio_ru_keys=%s snippet_keys=%s id=%s",
        idx,
        sorted(hit.keys()),
        sorted(biblio_ru.keys()),
        sorted(snippet_dict.keys()),
        str(hit.get("id") or ""),
      )

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

  @staticmethod
  def _normalize_markup_text(value: str) -> str:
    if not value:
      return ""
    # RosPatent uses <em> for highlights; MAX markdown supports ***text*** better.
    text = re.sub(r"(?is)<\s*em\s*>(.*?)<\s*/\s*em\s*>", r"***\1***", value)
    text = re.sub(r"(?is)<[^>]+>", "", text)
    return html.unescape(text).strip()

  @staticmethod
  def _stringify(value: Any) -> str:
    if value is None:
      return ""
    if isinstance(value, str):
      return value.strip()
    if isinstance(value, dict):
      for key in ("name", "value", "title", "text", "ru", "en"):
        nested = value.get(key)
        if isinstance(nested, str) and nested.strip():
          return nested.strip()
      return ""
    if isinstance(value, list):
      parts = [RosPatentApiClient._stringify(item) for item in value]
      compact = [part for part in parts if part]
      return ", ".join(compact)
    return str(value).strip()

  @staticmethod
  def _extract_text_field(source: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
      value = RosPatentApiClient._stringify(source.get(key))
      if value:
        return RosPatentApiClient._normalize_markup_text(value)
    return ""

  @staticmethod
  def _extract_document_info(raw_hit: dict[str, Any], biblio_ru: dict[str, Any], fallback_id: str) -> str:
    document = RosPatentApiClient._extract_text_field(
      biblio_ru,
      ("document", "doc_number", "document_number", "publication_number", "patent_number", "number"),
    )
    kind = RosPatentApiClient._extract_text_field(biblio_ru, ("kind", "kind_code", "document_kind"))
    country = RosPatentApiClient._extract_text_field(biblio_ru, ("country", "country_code", "office"))

    if not document:
      # A few payloads include document marker outside biblio.ru.
      document = RosPatentApiClient._extract_text_field(
        raw_hit,
        ("document", "doc_number", "document_number", "publication_number", "patent_number"),
      )
    if not document:
      document = fallback_id

    return " ".join(part for part in (country, document, kind) if part).strip()
