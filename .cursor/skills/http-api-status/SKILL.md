---
name: http-api-status
description: >-
  Chooses precise HTTP status codes and distinct error types for API responses
  (200, 201, 204, 400, 401, 403, 404, 409, 422, 429, 500, etc.) instead of a
  generic 400/500 or a 2xx body that wraps an error. Use when designing,
  implementing, documenting, or reviewing HTTP APIs, REST endpoints, OpenAPI
  status codes, rate limits, auth failures, or error responses, in any language.
---

# HTTP API status codes

Language-agnostic. Status and error-type selection only. In this repo the API is FastAPI and the error body is `application/problem+json`.

## Owns

Which HTTP status each success and failure case returns; keeping those cases distinct in the error payload.

## Rules

1. Pick the most specific registered status that matches the case. Generic 400 or 500 only when nothing more specific applies.
2. Never put an error in a 2xx body.
3. 500 is only unexpected server failure.
4. Distinct cases stay distinct in both status and error `type`.
5. FastAPI route `responses` should list the statuses the handler can return.

## Success

| Status | When |
| --- | --- |
| **200** | Read or in-place update that returns a representation |
| **201** | A resource was created. Include `Location`. |
| **202** | Accepted for async processing |
| **204** | Success with no body |

POST that does not create a resource returns 200. `POST /projects/{id}/analyze` returns 202.

## Client errors

| Status | When |
| --- | --- |
| **400** | Unparseable or structurally invalid request |
| **404** | Target resource does not exist |
| **409** | Conflicts with current state, including an analyze job already running |
| **422** | Body parsed, but a field or business rule is invalid |

**400 vs 422:** schema-structure failed → 400. Parsed but values are illegal → 422.

## Error payload

[RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) Problem Details (`application/problem+json`):

- `type` — stable identifier for this case
- `title` — short summary
- `status` — same as the HTTP status
- `detail` — human-readable, no internals

Never leak stack traces, SQL, or secrets.
