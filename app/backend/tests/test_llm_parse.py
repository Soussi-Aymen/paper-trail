from papertrail.config import Settings
from papertrail.llm import MillSignal, TokenFactoryError, _parse_model, build_client, missing_env


def _blank() -> Settings:
    return Settings(
        token_factory_api_key="",
        token_factory_base_url="",
        chat_model_small="",
        chat_model_large="",
        embedding_model="",
    )


def test_parse_model_reads_json_wrapped_in_a_fence():
    parsed = _parse_model('```json\n{"outcome":"warn","fact":"boilerplate"}\n```', MillSignal)
    assert parsed is not None
    assert parsed.outcome == "warn"


def test_parse_model_rejects_empty_text_and_text_without_an_object():
    assert _parse_model(None, MillSignal) is None
    assert _parse_model("   ", MillSignal) is None
    assert _parse_model("no braces here", MillSignal) is None


def test_parse_model_rejects_json_that_is_not_an_object():
    assert _parse_model("[1, 2]", MillSignal) is None


def test_missing_env_lists_each_blank_setting_and_build_client_refuses():
    missing = missing_env(_blank())
    assert missing == [
        "TOKEN_FACTORY_API_KEY",
        "TOKEN_FACTORY_BASE_URL",
        "CHAT_MODEL_SMALL",
        "CHAT_MODEL_LARGE",
        "EMBEDDING_MODEL",
    ]
    try:
        build_client(_blank())
    except TokenFactoryError as exc:
        assert "TOKEN_FACTORY_API_KEY" in str(exc)
    else:
        raise AssertionError("build_client should refuse a blank configuration")


def test_missing_env_is_empty_when_every_setting_is_present():
    settings = Settings(
        token_factory_api_key="key",
        token_factory_base_url="https://example.test/v1",
        chat_model_small="small",
        chat_model_large="large",
        embedding_model="embed",
    )
    assert missing_env(settings) == []
