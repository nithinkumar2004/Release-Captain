from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time


def issue_session_token(subject: str, signing_secret: str, ttl_seconds: int = 900) -> str:
    if len(signing_secret) < 32:
        raise ValueError("Hosted session signing secret must contain at least 32 characters.")
    if not subject or ttl_seconds < 1 or ttl_seconds > 3600:
        raise ValueError("Subject and a token lifetime between 1 and 3600 seconds are required.")
    payload = json.dumps(
        {"sub": subject, "exp": int(time.time()) + ttl_seconds},
        separators=(",", ":"),
    ).encode()
    encoded = base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
    signature = hmac.new(signing_secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def verify_session_token(token: str, signing_secret: str) -> bool:
    if len(signing_secret) < 32:
        return False
    try:
        encoded, signature = token.split(".", maxsplit=1)
        expected = hmac.new(signing_secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        return (
            isinstance(payload, dict)
            and isinstance(payload.get("sub"), str)
            and bool(payload["sub"])
            and isinstance(payload.get("exp"), int)
            and not isinstance(payload.get("exp"), bool)
            and int(time.time()) < payload["exp"]
            and payload["exp"] <= int(time.time()) + 3600
        )
    except (ValueError, TypeError, json.JSONDecodeError):
        return False
