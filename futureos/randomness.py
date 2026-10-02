"""Portable, versioned pseudorandomness for the synthetic kernel.

SplitMix64 advances a 64-bit state by a fixed increment for every draw.
Probability endpoints consume no draw; choice/shuffle use rejection sampling.
This generator is for reproducible experiments, not cryptographic use.
"""

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Sequence, TypeVar


RNG_ALGORITHM = "splitmix64-v1"
RNG_POLICY = "sha256-path-splitmix64-v1"
UINT64_MAX = (1 << 64) - 1
_INCREMENT = 0x9E3779B97F4A7C15
_T = TypeVar("_T")


def validate_seed(seed: int) -> None:
    if type(seed) is not int or not 0 <= seed <= UINT64_MAX:
        raise ValueError("seed must be an unsigned 64-bit integer")


def derive_seed(root_seed: int, *path: str | int) -> int:
    """Derive a portable seed from typed context identifiers.

    The versioned domain, root seed and path are encoded as canonical JSON
    (sorted keys, compact separators, UTF-8 without ASCII escaping). Each path
    component retains its type, so integer 1 and string "1" are distinct. The
    seed is the first eight SHA-256 digest bytes interpreted as big-endian.
    """
    validate_seed(root_seed)
    if not path:
        raise ValueError("RNG path must contain at least one component")
    typed_path: list[list[str | int]] = []
    for component in path:
        if type(component) is str:
            if not component:
                raise ValueError("RNG path strings must be nonempty valid UTF-8")
            try:
                component.encode("utf-8")
            except UnicodeEncodeError as error:
                raise ValueError("RNG path strings must be nonempty valid UTF-8") from error
            typed_path.append(["str", component])
        elif type(component) is int and component >= 0:
            typed_path.append(["int", component])
        else:
            raise ValueError("RNG path components must be strings or nonnegative integers")
    payload = {"domain": RNG_POLICY, "root_seed": root_seed, "path": typed_path}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big")


@dataclass(frozen=True, slots=True)
class RandomStreams:
    """Stateless factory for independent streams indexed by semantic context.

    Every call returns a fresh generator at the beginning of the requested
    stream. Reusing a context therefore repeats its draws; callers must supply
    a unique tick, agent, event, pair or occurrence path for independent uses.
    No generators are cached and stream consumption never changes this factory.
    """

    root_seed: int

    def __post_init__(self) -> None:
        validate_seed(self.root_seed)

    def stream(self, namespace: str, *path: str | int) -> "SeededRandom":
        """Create a stream for any nonempty UTF-8 namespace and typed path."""
        if type(namespace) is not str:
            raise ValueError("RNG namespace must be a nonempty valid UTF-8 string")
        return SeededRandom(derive_seed(self.root_seed, namespace, *path))


@dataclass(frozen=True, slots=True)
class RandomState:
    seed: int
    state: int
    draws: int = 0
    algorithm: str = RNG_ALGORITHM

    def __post_init__(self) -> None:
        validate_seed(self.seed)
        if self.algorithm != RNG_ALGORITHM:
            raise ValueError(f"unsupported RNG algorithm: {self.algorithm!r}")
        if type(self.state) is not int or not 0 <= self.state <= UINT64_MAX:
            raise ValueError("RNG state must be an unsigned 64-bit integer")
        if type(self.draws) is not int or self.draws < 0:
            raise ValueError("RNG draws must be a nonnegative integer")
        expected = (self.seed + self.draws * _INCREMENT) & UINT64_MAX
        if self.state != expected:
            raise ValueError("RNG state is inconsistent with seed and draw counter")


class SeededRandom:
    """An independent stream that can resume from its complete RandomState."""

    def __init__(self, seed: int) -> None:
        validate_seed(seed)
        self._seed = seed
        self._state = seed
        self._draws = 0

    @property
    def state(self) -> RandomState:
        return RandomState(self._seed, self._state, self._draws)

    @classmethod
    def from_state(cls, state: RandomState) -> "SeededRandom":
        if not isinstance(state, RandomState):
            raise ValueError("RNG state must be a RandomState")
        state.__post_init__()
        generator = cls(state.seed)
        generator._state = state.state
        generator._draws = state.draws
        return generator

    def _next_uint64(self) -> int:
        self._state = (self._state + _INCREMENT) & UINT64_MAX
        self._draws += 1
        value = self._state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & UINT64_MAX
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & UINT64_MAX
        return value ^ (value >> 31)

    def random(self) -> float:
        """Return a float in [0, 1), using the output's upper 53 bits."""
        return (self._next_uint64() >> 11) / (1 << 53)

    def probability(self, probability: float) -> bool:
        try:
            finite = type(probability) in (int, float) and math.isfinite(probability)
        except OverflowError:
            finite = False
        if not finite or not 0 <= probability <= 1:
            raise ValueError("probability must be a finite number in [0, 1]")
        if probability == 0:
            return False
        if probability == 1:
            return True
        return self.random() < probability

    def _index(self, size: int) -> int:
        # Reject the short tail to give every index the same number of outputs.
        limit = (1 << 64) - ((1 << 64) % size)
        while True:
            value = self._next_uint64()
            if value < limit:
                return value % size

    def choice(self, items: Sequence[_T]) -> _T:
        if not items:
            raise ValueError("cannot choose from an empty sequence")
        return items[self._index(len(items))]

    def shuffle(self, items: Sequence[_T]) -> list[_T]:
        """Return a shuffled copy; never mutate the caller's collection."""
        result = list(items)
        for position in range(len(result) - 1, 0, -1):
            selected = self._index(position + 1)
            result[position], result[selected] = result[selected], result[position]
        return result
