"""Shared, retrying LLM invocation adapter for the existing agent nodes."""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import BaseMessage
from langchain_groq import ChatGroq


class LLMInvocationError(RuntimeError):
    """Raised after an LLM request has exhausted its retry budget."""


class RetryingLLM:
    """Wrap a LangChain chat model with bounded retries and useful logging."""

    def __init__(
        self,
        llm: ChatGroq,
        *,
        retries: int,
        retry_base_seconds: float,
        logger: logging.Logger,
    ) -> None:
        self._llm = llm
        self._retries = retries
        self._retry_base_seconds = retry_base_seconds
        self._logger = logger

    def invoke(self, messages: Sequence[BaseMessage]) -> str:
        """Invoke the model, retrying transient provider or network failures."""
        last_error: Exception | None = None
        for attempt in range(1, self._retries + 1):
            try:
                response = self._llm.invoke(list(messages))
                content: Any = response.content
                if isinstance(content, str) and content.strip():
                    return content.strip()
                if isinstance(content, list):
                    text = "".join(
                        part.get("text", "") if isinstance(part, dict) else str(part)
                        for part in content
                    ).strip()
                    if text:
                        return text
                raise LLMInvocationError("The model returned an empty response.")
            except Exception as exc:
                last_error = exc
                if attempt == self._retries:
                    break
                delay = self._retry_base_seconds * (2 ** (attempt - 1))
                self._logger.warning(
                    "LLM request failed (attempt %s/%s): %s. Retrying in %.1fs.",
                    attempt,
                    self._retries,
                    exc,
                    delay,
                )
                time.sleep(delay)

        raise LLMInvocationError(
            f"LLM request failed after {self._retries} attempts."
        ) from last_error
