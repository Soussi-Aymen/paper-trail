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

Language-agnostic. Status and error-type selection only — not framework wiring.

## Owns

Which HTTP status each success and failure case returns; keeping those cases distinct in the error payload; declaring them on the API contract.

## Does not cover

- Language, framework, router, or handler implementation
- Auth mechanism (tokens, sessions) — only 401 vs 403 vs 404
- Rate-limiter implementation — only 429 + `Retry-After`
- Inventing statuses outside the IANA HTTP status code registry

If another loaded skill or the repo already settles the error envelope, use that envelope. Fill it with the statuses and distinct types this skill requires.

## Rules

1. Pick the **most specific registered status** that matches the case. Generic 400 or 500 only when nothing more specific applies.
2. Never put an error in a 2xx body. Never use 200/201 as a catch-all success.
3. **500 is only unexpected server failure.** Validation, auth, missing resources, conflicts, and rate limits are never 500.
4. Distinct cases stay distinct in **both** status **and** error `type`. Unauthorized, forbidden, not-found, malformed body, semantic validation, conflict, and rate-limited are different cases — not one `400 { error: "Bad request" }`.
5. Declare every status an operation can return on the API contract (OpenAPI or equivalent). Clients should not discover codes only at runtime.

## Success

| Status | When |
| --- | --- |
| **200** | Read or in-place update that returns a representation |
| **201** | A resource was created. Include `Location` of the new resource. Typical for POST create. |
| **202** | Accepted for async processing; the resource is not ready yet |
| **204** | Success with no body. Typical for DELETE, or PUT/PATCH that returns nothing |
| **304** | Conditional GET: representation unchanged |

POST that does not create a resource (search, action) → 200, not 201. PUT upsert: 201 if created, 200 if replaced — stay consistent.

## Client errors (never 500)

| Status | When |
| --- | --- |
| **400** | Unparseable or structurally invalid request (bad JSON, wrong types, missing required fields) |
| **401** | Missing or invalid authentication. Include `WWW-Authenticate` when applicable. Not logged in ≠ not allowed. |
| **403** | Authenticated but not permitted to perform this action |
| **404** | Target resource does not exist. Also use instead of 403 when revealing existence would leak it. |
| **405** | Method not allowed on this resource. Include `Allow`. |
| **406** | Cannot produce a representation matching `Accept` |
| **409** | Conflicts with current state (duplicate unique resource, version clash) |
| **410** | Resource gone and will not return |
| **412** | Conditional request failed (`If-Match` / `If-None-Match`) |
| **413** | Payload too large |
| **415** | `Content-Type` not supported |
| **422** | Body parsed, but a field or business rule is semantically invalid |
| **429** | Rate limited. Include `Retry-After`. Use 429 even if the request would also fail another check. |

**400 vs 422:** could not parse / schema-structure failed → 400. Parsed but values are illegal → 422. Do not dump both into 400.

**401 vs 403:** no usable credentials → 401. Known caller, insufficient permission → 403.

**403 vs 404:** default 403 when the caller must learn they are denied; 404 when existence is sensitive.

**409 vs 422:** duplicate or state conflict → 409. Field/rule validation on a new or updated body → 422.

**DELETE missing:** 404, unless this API documents idempotent delete as 204 — pick one and apply it everywhere.

## Server errors

| Status | When |
| --- | --- |
| **500** | Bug or unhandled failure only. Never a stand-in for a client mistake. |
| **501** | Known unimplemented capability |
| **502** | Valid request, upstream dependency returned a bad response |
| **503** | Temporarily unavailable. Include `Retry-After` when known. |
| **504** | Upstream timeout |

## Error payload

If the project already has an error envelope, use it. Otherwise [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) Problem Details (`application/problem+json`):

- `type` — stable identifier for **this** case (URI or URN). Clients switch on `type`, not on a generic message string.
- `title` — short, stable summary
- `status` — same as the HTTP status
- `detail` — human-readable, no internals
- extension members as needed (`errors` for field lists, retry hints)

Never leak stack traces, SQL, filesystem paths, or secret values. `type` must differ across distinct cases even when `status` is the same (several 400s, several 409s).

## Contract

For each operation, list the success status and every error status that operation can actually emit. A global "default 500" is not a substitute for 401/403/404/409/422/429 on the operations that produce them.
