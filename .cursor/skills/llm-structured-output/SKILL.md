---
name: llm-structured-output
description: >-
  Parses LLM JSON for papertrail through Nebius Token Factory. Use when
  editing query expansion, the paper-mill check, or grounded explanations.
---

# LLM structured output

- Chat and embeddings use `TOKEN_FACTORY_API_KEY`, `TOKEN_FACTORY_BASE_URL`, `CHAT_MODEL_SMALL`, `CHAT_MODEL_LARGE`, and `EMBEDDING_MODEL`. Do not add a second provider.
- Temperature is 0. Ask for JSON only. Include `PROMPT_VERSION` in the prompt so a prompt change misses the cache.
- Strip markdown fences, then parse with a Pydantic model. Do not trust `json.loads` into a bare dict.
- On invalid JSON, retry up to 2 times. Then continue without that model output.
- A quote used in an explanation must be a verbatim substring of the abstracts that were sent. Check that in code, not only in the prompt.
- Never log or return the API key.
