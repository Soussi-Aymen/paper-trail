"""One embeddings call and one chat call per configured model."""

import json
import sys

import httpx

from papertrail.config import get_settings
from papertrail.llm import TokenFactoryError, build_client, missing_env


def main() -> int:
    settings = get_settings()
    missing = missing_env(settings)
    if missing:
        _print_models(settings)
        print("Missing Token Factory settings: " + ", ".join(missing), file=sys.stderr)
        return 2
    try:
        client = build_client(settings)
        embedding = client.embeddings.create(
            model=settings.embedding_model.strip(),
            input="papertrail connectivity check",
            encoding_format="float",
        )
        if not embedding.data or not embedding.data[0].embedding:
            print("embeddings response did not include a vector", file=sys.stderr)
            return 1
        small = _chat(client, settings.chat_model_small.strip())
        large = _chat(client, settings.chat_model_large.strip())
    except TokenFactoryError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    vector = embedding.data[0].embedding
    print(
        json.dumps(
            {
                "embedding_model": embedding.model,
                "embedding_dimensions": len(vector),
                "chat_model_small": small["model"],
                "chat_small_reply": small["reply"],
                "chat_model_large": large["model"],
                "chat_large_reply": large["reply"],
            },
            indent=2,
        )
    )
    return 0


def _chat(client, model: str) -> dict:
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Reply with the single word ok."}],
        temperature=0,
        max_tokens=16,
    )
    reply = completion.choices[0].message.content if completion.choices else ""
    if not reply or not str(reply).strip():
        raise RuntimeError(f"{model} returned an empty reply")
    return {"model": completion.model, "reply": str(reply).strip()}


def _print_models(settings) -> None:
    if not settings.token_factory_api_key.strip() or not settings.token_factory_base_url.strip():
        return
    url = settings.token_factory_base_url.rstrip("/") + "/models"
    try:
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {settings.token_factory_api_key.strip()}"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        print(f"Could not list models: {exc}", file=sys.stderr)
        return
    ids = [item.get("id") for item in payload.get("data") or [] if item.get("id")]
    print("Available model ids:", file=sys.stderr)
    for model_id in ids:
        print(model_id, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
