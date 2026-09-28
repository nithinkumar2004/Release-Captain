from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from recap.llm.base import ProviderError


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        return None


def post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(request, timeout=60) as response:
            data = json.loads(response.read(2_000_001))
    except urllib.error.HTTPError as exc:
        raise ProviderError(f"AI provider returned HTTP {exc.code}.") from None
    except urllib.error.URLError as exc:
        raise ProviderError(
            f"AI provider connection failed: {exc.reason.__class__.__name__}."
        ) from None
    except (TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ProviderError(
            f"AI provider response was invalid ({exc.__class__.__name__})."
        ) from None
    if not isinstance(data, dict):
        raise ProviderError("AI provider returned an unexpected response.")
    return data
