from __future__ import annotations

import os
from getpass import getpass

from recap.credentials.models import EphemeralCredential

PROVIDER_ENV_VARS = {
    "openrouter": "RECAP_OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "hosted": "RECAP_HOSTED_TOKEN",
}


class CredentialManager:
    def acquire(self, provider: str, *, allow_prompt: bool = True) -> EphemeralCredential:
        try:
            env_name = PROVIDER_ENV_VARS[provider]
        except KeyError as exc:
            raise ValueError(f"Unsupported credential provider: {provider}") from exc
        if allow_prompt:
            prompt = (
                "Release Captain session token"
                if provider == "hosted"
                else f"{provider.title()} API key"
            )
            value = getpass(f"{prompt}: ")
        else:
            env_value = os.environ.get(env_name)
            if env_value is None:
                raise ValueError(f"Set {env_name} to use {provider} in non-interactive mode.")
            value = env_value
        return EphemeralCredential.create(provider, value)
