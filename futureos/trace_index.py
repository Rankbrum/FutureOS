# M5 — Index derivado do trace (não substitui fonte primária)
# Lazy: reconstruível a partir do trace; não altera hash externo.
class TraceIndex:
    """Incremental index agent -> record positions (references, not copies)."""
    def __init__(self):
        self.index = {}  # agent_id -> list of int positions
    def add(self, record_index: int, agent_ids: list[str]):
        for a in agent_ids:
            self.index.setdefault(a, []).append(record_index)
    def get(self, agent_id: str) -> list[int]:
        return self.index.get(agent_id, [])
    # ponytail: rebuilt from trace; not source of truth; kept minimal.
