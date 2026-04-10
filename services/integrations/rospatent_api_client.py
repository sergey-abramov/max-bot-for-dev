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
    common = raw_hit.get("common")
    common_dict = common if isinstance(common, dict) else {}
    biblio_merged = self._merge_biblio_locales(raw_hit.get("biblio"))

    title_src = str(snippet.get("title") or biblio_merged.get("title") or "").strip()
    title = self._normalize_markup_text(title_src)
    description = self._normalize_markup_text(str(snippet.get("description") or "").strip())

    document = self._format_document_line(common_dict, hit_id)
    publication_date = self._extract_publication_date(common_dict, biblio_merged)

    applicant = self._first_non_empty(
      self._normalize_markup_text(self._stringify(snippet.get("applicant"))),
      self._extract_text_field(biblio_merged, ("applicant", "applicants", "holder", "holders", "patentee")),
    )
    author = self._first_non_empty(
      self._normalize_markup_text(self._stringify(snippet.get("inventor"))),
      self._extract_text_field(biblio_merged, ("inventor", "inventors", "author", "authors")),
    )
    ipc = self._first_non_empty(
      self._ipc_from_classification(snippet.get("classification")),
      self._ipc_from_classification(common_dict.get("classification")),
      self._extract_text_field(biblio_merged, ("ipc", "ipc_index", "mki", "mpk", "classification")),
    )

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
      biblio_locales: list[str] = []
      if isinstance(biblio, dict):
        for loc, block in biblio.items():
          if isinstance(block, dict) and block:
            biblio_locales.append(f"{loc}:{sorted(block.keys())}")
      snippet = hit.get("snippet")
      snippet_dict = snippet if isinstance(snippet, dict) else {}
      common = hit.get("common")
      common_keys = sorted(common.keys()) if isinstance(common, dict) else []

      logger.info(
        "RosPatent hit schema sample #%s: top_keys=%s common_keys=%s biblio_locales=%s snippet_keys=%s id=%s",
        idx,
        sorted(hit.keys()),
        common_keys,
        biblio_locales,
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
    # API returns <em> for search highlights; MAX shows markdown literally, so keep inner text only.
    text = re.sub(r"(?is)<\s*em\s*>(.*?)<\s*/\s*em\s*>", r"\1", value)
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
  def _merge_biblio_locales(biblio: Any) -> dict[str, Any]:
    """Flatten biblio.{ru,en,ko,...} into one dict; later keys do not override non-empty earlier values."""
    if not isinstance(biblio, dict):
      return {}
    priority = ("ru", "en")
    merged: dict[str, Any] = {}
    for loc in priority:
      block = biblio.get(loc)
      if isinstance(block, dict):
        for key, val in block.items():
          if key not in merged or not RosPatentApiClient._stringify(merged.get(key)):
            merged[key] = val
    for loc, block in biblio.items():
      if loc in priority or not isinstance(block, dict):
        continue
      for key, val in block.items():
        if key not in merged or not RosPatentApiClient._stringify(merged.get(key)):
          merged[key] = val
    return merged

  @staticmethod
  def _first_non_empty(*values: str) -> str:
    for value in values:
      if value and value.strip():
        return value.strip()
    return ""

  @staticmethod
  def _format_document_line(common: dict[str, Any], fallback_id: str) -> str:
    office = RosPatentApiClient._stringify(common.get("publishing_office"))
    number = RosPatentApiClient._stringify(common.get("document_number"))
    kind = RosPatentApiClient._stringify(common.get("kind"))
    if office and number and kind:
      return f"{office} {number} {kind}".strip()
    if office and number:
      return f"{office} {number}".strip()
    if number and kind:
      return f"{number} {kind}".strip()
    return fallback_id

  @staticmethod
  def _extract_publication_date(common: dict[str, Any], biblio_merged: dict[str, Any]) -> str:
    from_common = RosPatentApiClient._stringify(common.get("publication_date"))
    if from_common:
      return from_common
    return RosPatentApiClient._extract_text_field(
      biblio_merged,
      (
        "publication_date",
        "publishing_date",
        "published_at",
        "date_publish",
        "pub_date",
        "date",
      ),
    )

  @staticmethod
  def _ipc_from_classification(classification: Any) -> str:
    if classification is None:
      return ""
    if isinstance(classification, str):
      return RosPatentApiClient._normalize_markup_text(classification.strip())
    if not isinstance(classification, dict):
      return ""
    ipc_raw = classification.get("ipc")
    if isinstance(ipc_raw, str) and ipc_raw.strip():
      return RosPatentApiClient._normalize_markup_text(ipc_raw.strip())
    if isinstance(ipc_raw, list):
      codes: list[str] = []
      for item in ipc_raw:
        if isinstance(item, dict):
          fullname = RosPatentApiClient._stringify(item.get("fullname"))
          if fullname:
            codes.append(fullname)
        elif isinstance(item, str) and item.strip():
          codes.append(item.strip())
      return RosPatentApiClient._normalize_markup_text(", ".join(codes))
    return ""
