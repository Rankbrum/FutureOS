"""Strict dataclass encoding with an explicit legacy simulation contract."""

from dataclasses import asdict, fields, is_dataclass
import json
import math
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

from .models import Simulation
from .validation import validate_json, validate_simulation


def canonical_json(value: Any) -> str:
    validate_json(value)
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (RecursionError, OverflowError) as error:
        raise ValueError(f"Invalid JSON: {error}") from error


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def parse_json(text: str) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"Non-finite JSON number: {value}")

    try:
        result = json.loads(text, object_pairs_hook=_unique_object,
                            parse_constant=reject_constant)
        validate_json(result)
        return result
    except (TypeError, json.JSONDecodeError, RecursionError, OverflowError) as error:
        raise ValueError(f"Invalid JSON: {error}") from error


def _json_value(value: Any, path: str) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list:
        return [_json_value(item, path) for item in value]
    if type(value) is dict and all(type(key) is str for key in value):
        return {key: _json_value(item, f"{path}.{key}") for key, item in value.items()}
    raise ValueError(f"{path}: expected a finite JSON value")


def _decode(annotation: Any, value: Any, path: str, *,
            preserve_numeric_types: bool = False) -> Any:
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is Literal:
        if any(type(value) is type(candidate) and value == candidate for candidate in args):
            return value
        raise ValueError(f"{path}: unsupported value")
    if origin in (Union, UnionType):
        # Preserve integers when both int/float are legal. Otherwise an audit
        # frame's cumulative counts become floats and change its chain bytes.
        candidates = sorted(args, key=lambda candidate: candidate is not type(value))
        for candidate in candidates:
            try:
                return _decode(candidate, value, path,
                               preserve_numeric_types=preserve_numeric_types)
            except ValueError:
                pass
        raise ValueError(f"{path}: incompatible value")
    if annotation is type(None):
        if value is None:
            return None
    elif is_dataclass(annotation):
        if type(value) is not dict:
            raise ValueError(f"{path}: expected object")
        expected = {field.name for field in fields(annotation)}
        if set(value) != expected:
            raise ValueError(f"{path}: missing or unknown fields: {sorted(expected ^ set(value))}")
        hints = get_type_hints(annotation)
        decoded = {}
        for field in fields(annotation):
            item_path = f"{path}.{field.name}"
            if field.name in ("payload", "metadata"):
                if type(value[field.name]) is not dict:
                    raise ValueError(f"{item_path}: expected object")
                decoded[field.name] = _json_value(value[field.name], item_path)
            else:
                decoded[field.name] = _decode(hints[field.name], value[field.name], item_path,
                                             preserve_numeric_types=preserve_numeric_types)
        return annotation(**decoded)
    elif origin is list and type(value) is list:
        return [_decode(args[0], item, f"{path}[{i}]",
                        preserve_numeric_types=preserve_numeric_types)
                for i, item in enumerate(value)]
    elif origin is dict and type(value) is dict:
        if args[0] is not str or any(type(key) is not str for key in value):
            raise ValueError(f"{path}: expected string object keys")
        return {key: _decode(args[1], item, f"{path}.{key}",
                            preserve_numeric_types=preserve_numeric_types)
                for key, item in value.items()}
    elif annotation is bool and type(value) is bool:
        return value
    elif annotation is int and type(value) is int:
        return value
    elif annotation is float and type(value) in (int, float):
        try:
            if math.isfinite(value):
                return value if preserve_numeric_types else float(value)
        except OverflowError:
            pass
    elif annotation is str and type(value) is str:
        return value
    raise ValueError(f"{path}: invalid type or non-finite value")


def simulation_to_dict(simulation: Simulation) -> dict[str, Any]:
    validate_simulation(simulation)
    data = asdict(simulation)
    # Adding the optional M3 runtime state must not change the schema1 bytes,
    # checksums, snapshot identities, or experiment reports of legacy runs.
    if simulation.audit is None:
        del data["audit"]
    return data


def simulation_from_dict(data: dict[str, Any]) -> Simulation:
    validate_json(data, "simulation")
    legacy_fields = {field.name for field in fields(Simulation)} - {"audit"}
    if type(data) is dict and set(data) == legacy_fields:
        # No other absent fields receive defaults: incomplete or unknown JSON
        # still fails the exact dataclass schema below.
        data = {**data, "audit": None}
    # M3 commitments hash accepted JSON numeric types exactly. Preserve int
    # values in float fields there; legacy decoding retains its historical
    # float normalization.
    modern = type(data) is dict and data.get("audit") is not None
    simulation = _decode(Simulation, data, "simulation", preserve_numeric_types=modern)
    validate_simulation(simulation)
    return simulation
