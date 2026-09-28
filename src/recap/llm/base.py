from __future__ import annotations

from typing import Protocol


class AIProvider(Protocol):
    def analyze(self, context: str, credential: str) -> str: ...


class ProviderError(Exception):
    """A sanitized AI provider failure."""
