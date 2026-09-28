from recap.llm.base import ProviderError
from recap.llm.http import post_json


class OpenRouterProvider:
    def analyze(self, context: str, credential: str) -> str:
        data = post_json(
            "https://openrouter.ai/api/v1/chat/completions",
            {"Authorization": f"Bearer {credential}"},
            {
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "Review the supplied release summary. Give concise, actionable risks only.",
                    },
                    {"role": "user", "content": context},
                ],
            },
        )
        return _choice_text(data)


def _choice_text(data: dict[str, object]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderError("AI provider response did not contain a completion.")
    first = choices[0]
    if not isinstance(first, dict):
        raise ProviderError("AI provider response did not contain a completion.")
    message = first.get("message")
    if not isinstance(message, dict):
        raise ProviderError("AI provider response did not contain a completion.")
    content = message.get("content")
    if not isinstance(content, str):
        raise ProviderError("AI provider response did not contain a completion.")
    return content
