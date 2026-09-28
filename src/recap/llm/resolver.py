from recap.llm.anthropic import AnthropicProvider
from recap.llm.base import AIProvider
from recap.llm.hosted import HostedProvider
from recap.llm.openai import OpenAIProvider
from recap.llm.openrouter import OpenRouterProvider

PROVIDERS: dict[str, AIProvider] = {
    "openrouter": OpenRouterProvider(),
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "hosted": HostedProvider(),
}


def resolve_provider(name: str) -> AIProvider:
    try:
        return PROVIDERS[name]
    except KeyError as exc:
        raise ValueError(f"Unsupported AI provider: {name}") from exc
