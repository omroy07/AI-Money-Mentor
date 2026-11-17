"""One place for Groq chat calls: timeout, token cap, retries and a fallback result.

Prompts and responses are never logged, only the model, status and latency.
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.1-8b-instant"
DEFAULT_TIMEOUT = 15.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_TOKEN_CAP = 1024
BACKOFF_BASE = 0.5


@dataclass
class LLMResult:
    text: str
    source: str  # "groq" or "fallback"
    ok: bool
    error: Optional[str] = None  # "unavailable", "timeout", "rate_limited", "server_error", "error"
    latency_ms: int = 0
    attempts: int = 0


def _env_number(name, default, cast):
    try:
        return cast(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _classify(exc):
    """Return (error_code, retryable) for an exception from the Groq client."""
    status = getattr(exc, "status_code", None)
    name = type(exc).__name__.lower()
    if "timeout" in name:
        return "timeout", True
    if status == 429 or "ratelimit" in name:
        return "rate_limited", True
    if isinstance(status, int) and status >= 500:
        return "server_error", True
    if "connection" in name:
        return "server_error", True
    return "error", False


def complete(
    client,
    messages,
    *,
    model=DEFAULT_MODEL,
    temperature=0.7,
    max_tokens=None,
    fallback_text="",
    timeout=None,
    max_retries=None,
    sleep=time.sleep,
):
    """Run a chat completion and always return an LLMResult.

    Timeout and retry counts come from LLM_TIMEOUT_SECONDS and LLM_MAX_RETRIES
    unless passed in; max_tokens is capped at LLM_MAX_TOKENS. Retries use
    exponential backoff on 429, 5xx and timeouts only. When the client is
    missing or every attempt fails, the result has source="fallback" and
    text=fallback_text.
    """
    if client is None:
        return LLMResult(fallback_text, "fallback", False, "unavailable")

    timeout = timeout if timeout is not None else _env_number("LLM_TIMEOUT_SECONDS", DEFAULT_TIMEOUT, float)
    max_retries = max_retries if max_retries is not None else _env_number("LLM_MAX_RETRIES", DEFAULT_MAX_RETRIES, int)
    cap = _env_number("LLM_MAX_TOKENS", DEFAULT_TOKEN_CAP, int)
    kwargs = {"model": model, "messages": messages, "temperature": temperature, "timeout": timeout}
    kwargs["max_tokens"] = min(max_tokens, cap) if max_tokens else cap

    started = time.monotonic()
    last_error = "error"
    attempts = 0
    for attempt in range(max_retries + 1):
        attempts = attempt + 1
        try:
            res = client.chat.completions.create(**kwargs)
            text = (res.choices[0].message.content or "").strip()
            latency = int((time.monotonic() - started) * 1000)
            logger.info("llm call ok model=%s attempts=%d latency_ms=%d", model, attempts, latency)
            return LLMResult(text, "groq", True, None, latency, attempts)
        except Exception as exc:
            last_error, retryable = _classify(exc)
            logger.warning(
                "llm call failed model=%s attempt=%d error=%s", model, attempts, last_error
            )
            if not retryable or attempt >= max_retries:
                break
            sleep(BACKOFF_BASE * (2**attempt))

    latency = int((time.monotonic() - started) * 1000)
    return LLMResult(fallback_text, "fallback", False, last_error, latency, attempts)
