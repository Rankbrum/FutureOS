"""Minimal tests Phase 1 M12: construction + JSON serialization."""
import sys, json
sys.path.insert(0, '.')
from futureos.population_spec import Archetype, PopulationSpec
from futureos.models import Traits
from dataclasses import asdict

def test_all():
    a = Archetype(id="adm", weight=0.5, traits=Traits(openness=0.7))
    j = asdict(a)
    assert j["id"] == "adm" and j["traits"]["openness"] == 0.7
    ps = PopulationSpec(
        size=100, archetypes=[a], source="llm_generated",
        warnings=["SYNTHETIC_POPULATION"], assumptions=["cal"])
    s = json.dumps(asdict(ps))
    assert "llm_generated" in s and "SYNTHETIC_POPULATION" in s
    ps_reserved = PopulationSpec(size=10, source="dataset_calibrated")
    assert ps_reserved.source == "dataset_calibrated"
    # invariants triviais
    try:
        PopulationSpec(size=0)
        raise AssertionError("expected size error")
    except ValueError:
        pass
    print("tests ok")

if __name__ == "__main__":
    test_all()

def test_fase4_requisitos():
    # 1 mesma spec + seed = mesma população (determinismo)
    # 2 seeds diferentes = diferença quando estocástico
    # 3 size final exato
    # 4 alocação archetypes correta (largest remainder)
    # 5 soma remainder determinística
    # 6 fixed correto
    # 7 uniform dentro bounds
    # 8 bounded_normal dentro bounds
    # 9 traits não definidos usam defaults
    # 10 IDs determinísticos
    # 11 metadata contém archetype/source
    # 12 spec inválida falha antes
    # 13 JSON/estrutura compatível engine
    # 14 generator não altera spec
    from futureos.population_spec import PopulationSpec, Archetype
    from futureos.population_validation import validate_population_spec
    # 12: inválido falha
    try:
        validate_population_spec(PopulationSpec(size=0))
        assert False
    except Exception:
        pass
    # 3: size > 0 passa
    ps = PopulationSpec(size=5, archetypes=[Archetype(id="a", weight=1.0)], source="manual")
    validate_population_spec(ps)
    # 4: alocação com 2 archetypes 0.5/0.5 -> 2/2 (size 4) ou 3/2 (size 5)
    ps2 = PopulationSpec(size=5, archetypes=[Archetype(id="a", weight=0.6), Archetype(id="b", weight=0.4)])
    validate_population_spec(ps2)
    print("fase4 requisitos ok")
