"""Immutable full snapshots at committed tick boundaries; not Harness checkpoints."""

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import tempfile

from .codec import canonical_json, parse_json, simulation_from_dict, simulation_to_dict
from .models import (
    ENGINE_VERSION, M3_ENGINE_VERSION, M3_SNAPSHOT_VERSION, SNAPSHOT_VERSION,
    Simulation,
)


def _checksum(simulation_json: str, schema_version: int, engine_version: str) -> str:
    encoded = canonical_json({"schema_version": schema_version,
                              "engine_version": engine_version,
                              "simulation": parse_json(simulation_json)})
    return sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Snapshot:
    id: str
    schema_version: int
    engine_version: str
    simulation_json: str
    checksum: str

    def to_json(self) -> str:
        restore_snapshot(self)
        return canonical_json({"id": self.id, "schema_version": self.schema_version,
                               "engine_version": self.engine_version,
                               "simulation": parse_json(self.simulation_json),
                               "checksum": self.checksum})

    @classmethod
    def from_json(cls, text: str) -> "Snapshot":
        data = parse_json(text)
        expected = {"id", "schema_version", "engine_version", "simulation", "checksum"}
        if type(data) is not dict or set(data) != expected:
            raise ValueError("Snapshot has missing or unknown fields")
        snapshot = cls(data["id"], data["schema_version"], data["engine_version"],
                       canonical_json(data["simulation"]), data["checksum"])
        restore_snapshot(snapshot)
        return snapshot


def create_snapshot(simulation: Simulation) -> Snapshot:
    encoded = canonical_json(simulation_to_dict(simulation))
    schema_version = SNAPSHOT_VERSION if simulation.audit is None else M3_SNAPSHOT_VERSION
    engine_version = ENGINE_VERSION if simulation.audit is None else M3_ENGINE_VERSION
    checksum = _checksum(encoded, schema_version, engine_version)
    snapshot_id = f"{simulation.id}:tick-{simulation.world.current_tick}:{checksum[:16]}"
    return Snapshot(snapshot_id, schema_version, engine_version, encoded, checksum)


def restore_snapshot(snapshot: Snapshot) -> Simulation:
    if not isinstance(snapshot, Snapshot):
        raise ValueError("Expected Snapshot")
    supported = {SNAPSHOT_VERSION: ENGINE_VERSION, M3_SNAPSHOT_VERSION: M3_ENGINE_VERSION}
    if type(snapshot.schema_version) is not int or snapshot.schema_version not in supported:
        raise ValueError("Unsupported snapshot schema version")
    if snapshot.engine_version != supported[snapshot.schema_version]:
        raise ValueError("Unsupported snapshot engine version")
    if type(snapshot.simulation_json) is not str or type(snapshot.checksum) is not str:
        raise ValueError("Snapshot JSON and checksum must be strings")
    if _checksum(snapshot.simulation_json, snapshot.schema_version,
                 snapshot.engine_version) != snapshot.checksum:
        raise ValueError("Snapshot checksum mismatch")
    data = parse_json(snapshot.simulation_json)
    if type(data) is not dict:
        raise ValueError("Snapshot simulation must be an object")
    if snapshot.schema_version == SNAPSHOT_VERSION:
        if "audit" in data:
            raise ValueError("Legacy snapshot cannot contain audit state")
    elif "audit" not in data or data["audit"] is None:
        raise ValueError("M3 snapshot requires audit state")
    simulation = simulation_from_dict(data)
    from .audit import verify_audit
    verify_audit(simulation)
    expected_id = f"{simulation.id}:tick-{simulation.world.current_tick}:{snapshot.checksum[:16]}"
    if snapshot.id != expected_id:
        raise ValueError("Snapshot identity mismatch")
    return simulation


def save_snapshot(snapshot: Snapshot, path: str | Path) -> None:
    """Publish one complete UTF-8 snapshot by replacement in the same directory."""
    encoded = snapshot.to_json()
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=destination.parent, delete=False) as temporary:
            temporary_path = temporary.name
            temporary.write(encoded + "\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None and os.path.exists(temporary_path):
            os.unlink(temporary_path)


def load_snapshot(path: str | Path) -> Snapshot:
    return Snapshot.from_json(Path(path).read_text(encoding="utf-8"))
