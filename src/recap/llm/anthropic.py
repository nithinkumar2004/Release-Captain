from recap.llm.base import ProviderError
from recap.llm.http import post_json


class AnthropicProvider:
    def analyze(self, context: str, credential: str) -> str:
        data = post_json(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": credential, "anthropic-version": "2023-06-01"},
            {
                "model": "claude-3-5-haiku-latest",
                "max_tokens": 500,
                "system": "Review the release summary and return concise, actionable risks.",
                "messages": [{"role": "user", "content": context}],
            },
        )
        content = data.get("content")
        if not isinstance(content, list) or not content or not isinstance(content[0], dict):
            raise ProviderError("AI provider response did not contain a completion.")
        text = content[0].get("text")
        if not isinstance(text, str):
            raise ProviderError("AI provider response did not contain a completion.")
        return text
