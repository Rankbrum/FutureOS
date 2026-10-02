"""Explicit provider selection, with an offline fake available by default."""

from .llm_provider import FakeLLMProvider, LLMProvider, LLMUnavailable


class Registry:
    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider | type[LLMProvider]] = {}
        self.register("fake", FakeLLMProvider)

    def register(self, name: str, provider: LLMProvider | type[LLMProvider]) -> None:
        if type(name) is not str or not name.strip() or name != name.strip():
            raise ValueError("provider name must be a nonempty string without outer spaces")
        valid = isinstance(provider, LLMProvider) or (
            isinstance(provider, type) and issubclass(provider, LLMProvider)
            and provider is not LLMProvider
        )
        if not valid:
            raise ValueError("registered provider must implement LLMProvider")
        if name in self._providers:
            raise ValueError("provider name is already registered")
        self._providers[name] = provider

    def get(self, name: str) -> LLMProvider:
        if type(name) is not str or name not in self._providers:
            raise LLMUnavailable("selected LLM provider is not registered")
        provider = self._providers[name]
        if isinstance(provider, type):
            try:
                return provider()
            except Exception:
                # Provider initialization errors may contain credential material.
                raise LLMUnavailable("selected LLM provider could not initialize") from None
        return provider
