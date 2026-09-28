from __future__ import annotations

import re
from collections.abc import Iterable

SENSITIVE_FIELD = re.compile(
    r"(?i)\b(authorization|x-api-key|api[_-]?key|token|password|secret)\b"
    r"(\s*[:=]\s*)([^\s,;\"']+)"
)
BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
PROVIDER_KEY = re.compile(r"\b(?:sk-or-v1-|sk-)[A-Za-z0-9_-]{16,}\b")


def redact(text: str, known_secrets: Iterable[str] = ()) -> str:
    result = text
    for secret in known_secrets:
        if secret:
            result = result.replace(secret, "[REDACTED]")
    result = BEARER.sub("Bearer [REDACTED]", result)
    result = PROVIDER_KEY.sub("[REDACTED]", result)
    return SENSITIVE_FIELD.sub(r"\1\2[REDACTED]", result)
