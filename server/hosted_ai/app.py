from __future__ import annotations

import json
import os
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, ClassVar

from recap.llm.base import ProviderError
from recap.llm.http import post_json
from recap.llm.openrouter import _choice_text
from recap.security.redaction import redact
from server.hosted_ai.session_tokens import verify_session_token

MAX_BODY_BYTES = 20_000
RATE_LIMIT = 30
RATE_WINDOW_SECONDS = 60


class HostedAIHandler(BaseHTTPRequestHandler):
    _requests: ClassVar[defaultdict[str, deque[float]]] = defaultdict(deque)
    _rate_lock: ClassVar[Any] = threading.Lock()

    def do_POST(self) -> None:
        if self.path != "/v1/analyze":
            self._send(404, {"error": "not_found"})
            return
        if not self._within_rate_limit():
            self._send(429, {"error": "rate_limited"})
            return
        token = self.headers.get("Authorization", "")
        if not token.startswith("Bearer ") or not verify_session_token(
            token[7:], os.environ.get("RECAP_HOSTED_SESSION_SECRET", "")
        ):
            self._send(401, {"error": "unauthorized"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send(400, {"error": "invalid_content_length"})
            return
        if content_length < 1 or content_length > MAX_BODY_BYTES:
            self._send(413, {"error": "request_too_large"})
            return
        try:
            body = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send(400, {"error": "invalid_json"})
            return
        summary = body.get("summary") if isinstance(body, dict) else None
        if not isinstance(summary, str) or not summary.strip():
            self._send(400, {"error": "summary_required"})
            return
        upstream_key = os.environ.get("OPENROUTER_API_KEY")
        if not upstream_key:
            self._send(503, {"error": "service_unavailable"})
            return
        safe_summary = redact(summary, [token[7:], upstream_key])
        try:
            response = post_json(
                "https://openrouter.ai/api/v1/chat/completions",
                {"Authorization": f"Bearer {upstream_key}"},
                {
                    "model": os.environ.get("RECAP_HOSTED_MODEL", "openai/gpt-4o-mini"),
                    "messages": [
                        {
                            "role": "system",
                            "content": "Review this release summary for actionable risks.",
                        },
                        {"role": "user", "content": safe_summary[:MAX_BODY_BYTES]},
                    ],
                },
            )
            analysis = redact(_choice_text(response), [token[7:], upstream_key])
        except (ProviderError, ValueError):
            self._send(502, {"error": "upstream_failed"})
            return
        self._send(200, {"analysis": analysis})

    def _within_rate_limit(self) -> bool:
        now = time.monotonic()
        key = self.client_address[0]
        with self._rate_lock:
            if len(self._requests) > 2048:
                stale = [
                    address
                    for address, requests in self._requests.items()
                    if not requests or now - requests[-1] >= RATE_WINDOW_SECONDS
                ]
                for address in stale:
                    del self._requests[address]
            timestamps = self._requests[key]
            while timestamps and now - timestamps[0] >= RATE_WINDOW_SECONDS:
                timestamps.popleft()
            if len(timestamps) >= RATE_LIMIT:
                return False
            timestamps.append(now)
        return True

    def _send(self, status: int, body: dict[str, Any]) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    if not os.environ.get("RECAP_HOSTED_SESSION_SECRET"):
        raise SystemExit("RECAP_HOSTED_SESSION_SECRET must be configured.")
    host = os.environ.get("RECAP_HOSTED_BIND", "127.0.0.1")
    port = int(os.environ.get("RECAP_HOSTED_PORT", "8765"))
    with ThreadingHTTPServer((host, port), HostedAIHandler) as server:
        print(f"Hosted AI listening on {host}:{port}; terminate with Ctrl+C.")
        server.serve_forever()


if __name__ == "__main__":
    main()
