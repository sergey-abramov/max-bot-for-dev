# RosPatent `similar_search` Contract

This document fixes the integration contract for `POST /patsearch/v0.2/similar_search`
and describes how transport/domain outcomes map to bot UX messages.

## Endpoint

- URL: `https://searchplatform.rospatent.gov.ru/patsearch/v0.2/similar_search`
- Method: `POST`
- Headers:
  - `Authorization: Bearer <ROSPATENT_API_KEY>`
  - `Content-Type: application/json`

## Request Schema

Required fields:

- `type_search` (`string`) - must be `text_search`
- `pat_text` (`string`) - user query text
- `count` (`integer`) - requested number of results (bot scenario: `5`)

Example:

```json
{
  "type_search": "text_search",
  "pat_text": "Система очистки воды для промышленного производства",
  "count": 5
}
```

## Response Fields Used By Bot

Top-level:

- `hits` (`array`)

Per item:

- `hits[].id` (`string|number`) - patent identifier
- `hits[].snippet.title` (`string`) - title for card header
- `hits[].snippet.description` (`string`) - description snippet (truncated safely in UX)

## Error Codes And UX Mapping

- `401 Unauthorized`
  - Technical meaning: invalid/missing API key.
  - UX message: "Сервис поиска патентов временно недоступен: проблема с API ключом."
- `400 Bad Request`
  - Technical meaning: malformed or insufficient query payload.
  - UX message: "Уточните запрос (например, добавьте дату, город, отрасль, ключевые слова)."
- `500 Bad query syntax` (or other `5xx`)
  - Technical meaning: query syntax/internal search processing failure.
  - UX message: "Не удалось обработать запрос. Попробуйте уточнить формулировку."
- Network errors / timeout
  - Technical meaning: upstream unavailable or slow response.
  - UX message: "Сервис временно недоступен. Попробуйте позже."

## Successful Result Mapping To UX

- `hits` is empty:
  - UX message: "Ничего не найдено. Попробуйте переформулировать запрос."
- `hits` has items:
  - Render at most 5 cards.
  - Each card includes:
    - title from `snippet.title`
    - shortened description from `snippet.description`
    - link button "Открыть патент" built from `id` using the RosPatent patent page URL template chosen in handler/client implementation.
