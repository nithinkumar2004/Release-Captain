from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class EphemeralCredential:
    provider: str
    _value: bytearray = field(repr=False)

    @classmethod
    def create(cls, provider: str, value: str) -> EphemeralCredential:
        if not value.strip():
            raise ValueError("Credential cannot be empty.")
        return cls(provider=provider, _value=bytearray(value.strip().encode("utf-8")))

    def reveal(self) -> str:
        if not self._value:
            raise RuntimeError("Credential has already been cleared.")
        return self._value.decode("utf-8")

    def clear(self) -> None:
        for index in range(len(self._value)):
            self._value[index] = 0
        self._value.clear()
