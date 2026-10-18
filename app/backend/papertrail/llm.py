import re
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from papertrail.cache import cache_get, cache_put, json_key
from papertrail.config import Settings

PROMPT_VERSION = "1"
ModelT = TypeVar("ModelT", bound=BaseModel)


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


def embedding_key(settings: Settings, text: str) -> str:
    return json_key("emb", {"model": settings.embedding_model, "text": text.strip()})


def cached_embedding(session: Session, settings: Settings, text: str) -> list[float]:
    cleaned = text.strip()
    if not cleaned:
        return []
    cached = cache_get(session, embedding_key(settings, cleaned))
    if cached is None:
        return []
    values = cached.get("vector")
    return [float(item) for item in values] if isinstance(values, list) else []


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
        self.stopped_for_budget = False

    def chat(self, model: str, prompt: str, max_tokens: int = 700) -> str | None:
        key = json_key("llm", {"model": model, "prompt": prompt})
        cached = cache_get(self.session, key)
        if cached is not None:
            text = cached.get("text")
            return str(text) if text else None
        if self.calls >= self.settings.max_llm_calls_per_run:
            self.stopped_for_budget = True
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

    def chat_json(self, model: str, prompt: str, model_type: type[ModelT], max_tokens: int = 700) -> ModelT | None:
        versioned = f"PROMPT_VERSION={PROMPT_VERSION}\n{prompt}"
        key = json_key("llm-json", {"model": model, "prompt": versioned, "schema": model_type.__name__})
        cached = cache_get(self.session, key)
        if cached is not None and isinstance(cached.get("data"), dict):
            try:
                return model_type.model_validate(cached["data"])
            except ValidationError:
                pass
        for _attempt in range(3):
            raw = self._complete(model, versioned, max_tokens)
            parsed = _parse_model(raw, model_type)
            if parsed is not None:
                cache_put(self.session, key, "llm-json", {"data": parsed.model_dump()})
                return parsed
            if self.stopped_for_budget:
                return None
        return None

    def _complete(self, model: str, prompt: str, max_tokens: int) -> str | None:
        if self.calls >= self.settings.max_llm_calls_per_run:
            self.stopped_for_budget = True
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
        return completion.choices[0].message.content

    def embed(self, text: str) -> list[float]:
        cleaned = text.strip()
        if not cleaned:
            return []
        key = embedding_key(self.settings, cleaned)
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


class SearchQueries(BaseModel):
    queries: list[str] = []


class MillSignal(BaseModel):
    outcome: str = "pass"
    fact: str = ""


class GroundedQuote(BaseModel):
    paper: str = ""
    text: str = ""


class GroundedExplanation(BaseModel):
    explanation: str = ""
    grounded: bool = False
    quotes: list[GroundedQuote] = []


def _parse_model[ModelT: BaseModel](raw: str | None, model_type: type[ModelT]) -> ModelT | None:
    if not raw:
        return None
    text = raw.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return model_type.model_validate_json(text[start : end + 1])
    except ValidationError:
        return None
