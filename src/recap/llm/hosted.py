from __future__ import annotations

import os
from urllib.parse import urlsplit

from recap.core.errors import RecapError
from recap.llm.base import ProviderError
from recap.llm.http import post_json


class HostedProvider:
    def analyze(self, context: str, credential: str) -> str:
        endpoint = os.environ.get("RECAP_HOSTED_URL")
        if not endpoint:
            raise RecapError("Set RECAP_HOSTED_URL to use the hosted AI provider.")
        parsed_endpoint = urlsplit(endpoint)
        if parsed_endpoint.scheme != "https" or not parsed_endpoint.netloc:
            raise RecapError("RECAP_HOSTED_URL must be an HTTPS endpoint.")
        data = post_json(
            endpoint,
            {"Authorization": f"Bearer {credential}"},
            {"summary": context},
        )
        result = data.get("analysis")
        if not isinstance(result, str):
            raise ProviderError("Hosted AI response did not contain an analysis.")
        return result
