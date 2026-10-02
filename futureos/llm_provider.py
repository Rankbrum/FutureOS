"""Small, optional LLM contracts; no network clients or credentials.

The fake keeps requests in memory for tests. Responses are proposals and must
be validated by the calling feature before they enter a deterministic pipeline.
"""

from copy import deepcopy
from dataclasses import dataclass, field

from .codec import canonical_json
from .validation import validate_json


class ProviderError(Exception):
    """A provider could not produce a usable response."""


class LLMUnavailable(ProviderError):
    """The explicitly selected provider is unavailable."""


def _text(value: object, name: str) -> None:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError(f"{name} must be valid UTF-8") from error


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: str
    content: str = field(repr=False)

    def __post_init__(self) -> None:
        if self.role not in ("system", "user", "assistant"):
            raise ValueError("message role must be system, user or assistant")
        _text(self.content, "message content")


@dataclass(frozen=True, slots=True)
class UsageMetadata:
    input_tokens: int | None = None
    output_tokens: int | None = None

    def __post_init__(self) -> None:
        for name in ("input_tokens", "output_tokens"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{name} must be a nonnegative integer or None")


@dataclass(frozen=True, slots=True)
class LLMRequest:
    messages: list[LLMMessage]
    model: str | None = None
    metadata: dict = field(default_factory=dict, repr=False)
    response_format: str = "json"

    def __post_init__(self) -> None:
        if type(self.messages) is not list or not self.messages:
            raise ValueError("request messages must be a nonempty list")
        if not all(isinstance(message, LLMMessage) for message in self.messages):
            raise ValueError("request messages must contain LLMMessage values")
        if self.model is not None:
            _text(self.model, "request model")
        if type(self.metadata) is not dict:
            raise ValueError("request metadata must be a JSON object")
        validate_json(self.metadata, "request.metadata")
        if self.response_format not in ("json", "text"):
            raise ValueError("response_format must be json or text")


@dataclass(frozen=True, slots=True)
class LLMResponse:
    content: str = field(repr=False)
    provider: str = "fake"
    model: str | None = None
    usage: UsageMetadata = field(default_factory=UsageMetadata)

    def __post_init__(self) -> None:
        _text(self.content, "response content")
        _text(self.provider, "response provider")
        if self.model is not None:
            _text(self.model, "response model")
        if not isinstance(self.usage, UsageMetadata):
            raise ValueError("response usage must be UsageMetadata")


class LLMProvider:
    """Feature callers own response validation and persistence policy."""

    provider_name: str
    model: str | None

    def generate(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError


class FakeLLMProvider(LLMProvider):
    """An offline fixture, optionally returning a supplied response or error.

    Its default population proposal is deliberately generic. It does not infer
    facts or demographic statistics from the human description.
    """

    provider_name = "fake"

    def __init__(self, response: str | dict | LLMResponse | None = None, *,
                 error: ProviderError | None = None,
                 model: str = "fake-population-v1") -> None:
        if response is not None and not isinstance(response, (str, dict, LLMResponse)):
            raise ValueError("fake response must be text, JSON object or LLMResponse")
        if error is not None and not isinstance(error, ProviderError):
            raise ValueError("fake error must be ProviderError")
        _text(model, "fake model")
        self.model = model
        self._response = deepcopy(response)
        self._error = error
        self.requests: list[LLMRequest] = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not isinstance(request, LLMRequest):
            raise ProviderError("provider request must be LLMRequest")
        # Recheck mutable containers before recording an independent fixture.
        request.__post_init__()
        self.requests.append(deepcopy(request))
        if self._error is not None:
            raise self._error
        if isinstance(self._response, LLMResponse):
            return deepcopy(self._response)
        body = self._response
        if body is None and request.metadata.get("purpose") == "population_plan":
            requested_size = request.metadata.get("population_size")
            size = 100 if requested_size is None else requested_size
            if type(size) is not int or size < 1:
                raise ProviderError("population_size must be a positive integer")
            body = {
                "size": size,
                "archetypes": [{
                    "id": "synthetic_default", "weight": 1.0,
                    "traits": {
                        "openness": 0.5, "risk_tolerance": 0.5,
                        "price_sensitivity": 0.5, "influence": 0.5,
                        "conformity": 0.5,
                    },
                    "metadata": {},
                }],
                "relationship_policy": "random_sparse",
                "trait_distributions": {},
                "assumptions": [
                    "Esta população é sintética e não calibrada.",
                    "Traits e pesos são hipóteses para revisão humana.",
                    "A proposta não representa estatísticas da população real.",
                ],
                "source": "llm_generated",
                "warnings": ["SYNTHETIC_POPULATION", "UNCALIBRATED_POPULATION"],
                "metadata": {},
            }
        if body is None:
            body = "Summary derived from ScientistReport (fake)"
        content = canonical_json(body) if isinstance(body, dict) else body
        return LLMResponse(content=content, provider=self.provider_name, model=self.model)
