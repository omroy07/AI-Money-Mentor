from types import SimpleNamespace
from unittest.mock import MagicMock

from utils.llm_client import complete


class FakeError(Exception):
    def __init__(self, status_code=None):
        super().__init__("boom")
        self.status_code = status_code


class APITimeoutError(Exception):
    pass


def _ok(text="hello"):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=f"  {text}  "))]
    )


def _client(*outcomes):
    client = MagicMock()
    client.chat.completions.create.side_effect = list(outcomes)
    return client


MSGS = [{"role": "user", "content": "private prompt"}]


def test_success_returns_text_from_groq():
    client = _client(_ok("hi"))
    res = complete(client, MSGS, sleep=lambda s: None)
    assert res.ok and res.source == "groq" and res.text == "hi"
    assert res.attempts == 1
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["timeout"] == 15.0
    assert kwargs["max_tokens"] == 1024


def test_max_tokens_is_capped(monkeypatch):
    monkeypatch.setenv("LLM_MAX_TOKENS", "200")
    client = _client(_ok())
    complete(client, MSGS, max_tokens=5000, sleep=lambda s: None)
    assert client.chat.completions.create.call_args.kwargs["max_tokens"] == 200


def test_missing_client_returns_fallback():
    res = complete(None, MSGS, fallback_text="offline")
    assert not res.ok and res.source == "fallback"
    assert res.text == "offline" and res.error == "unavailable"


def test_timeout_retries_then_falls_back():
    client = _client(APITimeoutError(), APITimeoutError(), APITimeoutError())
    sleeps = []
    res = complete(client, MSGS, fallback_text="fb", sleep=sleeps.append)
    assert res.source == "fallback" and res.error == "timeout"
    assert res.attempts == 3
    assert sleeps == [0.5, 1.0]


def test_rate_limit_then_success():
    client = _client(FakeError(429), _ok("done"))
    sleeps = []
    res = complete(client, MSGS, sleep=sleeps.append)
    assert res.ok and res.text == "done" and res.attempts == 2
    assert sleeps == [0.5]


def test_server_error_is_retried():
    client = _client(FakeError(503), _ok())
    assert complete(client, MSGS, sleep=lambda s: None).ok


def test_client_error_is_not_retried():
    client = _client(FakeError(400), _ok())
    res = complete(client, MSGS, fallback_text="fb", sleep=lambda s: None)
    assert res.source == "fallback" and res.error == "error"
    assert client.chat.completions.create.call_count == 1


def test_retry_count_is_configurable(monkeypatch):
    monkeypatch.setenv("LLM_MAX_RETRIES", "0")
    client = _client(FakeError(429), _ok())
    res = complete(client, MSGS, sleep=lambda s: None)
    assert res.error == "rate_limited" and res.attempts == 1


def test_prompts_are_not_logged(caplog):
    client = _client(FakeError(500), FakeError(500), FakeError(500))
    with caplog.at_level("DEBUG"):
        complete(client, MSGS, sleep=lambda s: None)
    assert "private prompt" not in caplog.text
