from recap.llm.http import post_json
from recap.llm.openrouter import _choice_text


class OpenAIProvider:
    def analyze(self, context: str, credential: str) -> str:
        data = post_json(
            "https://api.openai.com/v1/chat/completions",
            {"Authorization": f"Bearer {credential}"},
            {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "Review this release summary for concise actionable risks.",
                    },
                    {"role": "user", "content": context},
                ],
            },
        )
        return _choice_text(data)
