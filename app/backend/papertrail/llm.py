import json

from openai import OpenAI
from sqlalchemy.orm import Session

from papertrail.cache import cache_get, cache_put, json_key
from papertrail.config import Settings


class TokenFactoryError(RuntimeError):
    pass


def missing_env(settings: Settings) -> list[str]:
    required = (
        ("token_factory_api_key", "TOKEN_FACTORY_API_KEY"),
        ("token_factory_base_url", "TOKEN_FACTORY_BASE_URL"),
        ("chat_model_small", "CHAT_MODEL_SMALL"),
        ("chat_model_large", "CHAT_MODEL_LARGE"),
        ("embedding_model", "EMBEDDING_MODEL"),
    )
    missing: list[str] = []
    for attr, name in required:
        if not str(getattr(settings, attr)).strip():
            missing.append(name)
    return missing


def build_client(settings: Settings) -> OpenAI:
    missing = missing_env(settings)
    if missing:
        names = ", ".join(missing)
        raise TokenFactoryError(f"Missing Token Factory settings: {names}")
    return OpenAI(
        api_key=settings.token_factory_api_key.strip(),
        base_url=settings.token_factory_base_url.strip(),
        timeout=60.0,
    )


class LanguageModel:
    def __init__(self, settings: Settings, session: Session, client: OpenAI) -> None:
        self.settings = settings
        self.session = session
        self.client = client
        self.calls = 0

    def chat(self, model: str, prompt: str, max_tokens: int = 700) -> str | None:
        key = json_key("llm", {"model": model, "prompt": prompt})
        cached = cache_get(self.session, key)
        if cached is not None:
            text = cached.get("text")
            return str(text) if text else None
        if self.calls >= self.settings.max_llm_calls_per_run:
            return None
        self.calls += 1
        completion = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=max_tokens,
        )
        if not completion.choices:
            return None
        text = completion.choices[0].message.content
        if text is None:
            return None
        cache_put(self.session, key, "llm", {"text": text})
        return text

    def embed(self, text: str) -> list[float]:
        cleaned = text.strip()
        if not cleaned:
            return []
        key = json_key("emb", {"model": self.settings.embedding_model, "text": cleaned})
        cached = cache_get(self.session, key)
        if cached is not None:
            values = cached.get("vector")
            return [float(item) for item in values] if isinstance(values, list) else []
        response = self.client.embeddings.create(
            model=self.settings.embedding_model.strip(),
            input=cleaned[:8000],
            encoding_format="float",
        )
        if not response.data:
            return []
        vector = [float(item) for item in response.data[0].embedding]
        cache_put(self.session, key, "emb", {"vector": vector})
        return vector


def parse_json_object(raw: str | None) -> dict | None:
    if not raw:
        return None
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None
    if isinstance(value, dict):
        return value
    return None
