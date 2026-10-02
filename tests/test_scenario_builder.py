"""M15 Scenario Builder tests — minimal manual suite."""
import pytest
from futureos.scenario_builder import (ScenarioSpec, BranchSpec, InterventionSpec, validate_scenario_spec, scenario_fingerprint, build_branch_events, scenario_from_json, scenario_to_json, apply_initial_state)
from futureos.models import Event

def test_valid_scenario():
    s = ScenarioSpec(id="s1", name="pricing", description="test", initial_state={"price":70}, duration_ticks=30, branches=[BranchSpec(id="A", name="stay", interventions=[])])
    validate_scenario_spec(s)

def test_duplicate_branch_ids():
    with pytest.raises(ValueError, match="unique"):
        s = ScenarioSpec(id="s1", name="bad", description="d", initial_state={}, duration_ticks=10, branches=[BranchSpec(id="A",name="x"),BranchSpec(id="A",name="y")])
        validate_scenario_spec(s)

def test_negative_duration():
    with pytest.raises(ValueError, match="duration_ticks"):
        s = ScenarioSpec(id="s1", name="bad", description="d", initial_state={}, duration_ticks=-1, branches=[])
        validate_scenario_spec(s)

def test_tick_out_of_horizon():
    with pytest.raises(ValueError, match="tick"):
        s = ScenarioSpec(id="s1",name="bad",description="d",initial_state={},duration_ticks=5,branches=[BranchSpec(id="A",name="x",interventions=[InterventionSpec(type="PRICE_CHANGE",tick=10,payload={"price":100})])])
        validate_scenario_spec(s)

def test_unknown_intervention():
    with pytest.raises(ValueError, match="Unsupported"): InterventionSpec(type="BAD_TYPE",tick=1,payload={"x":1})

def test_reach_invalid():
    with pytest.raises(ValueError, match="reach"): InterventionSpec(type="PRICE_CHANGE",tick=1,payload={"price":1},reach=1.5)

def test_payload_invalid():
    with pytest.raises(ValueError, match="payload"): InterventionSpec(type="PRICE_CHANGE",tick=1,payload={})

def test_json_roundtrip():
    s = ScenarioSpec(id="s1",name="pricing",description="Aumentar preço",initial_state={"price":70},duration_ticks=30,branches=[BranchSpec(id="A",name="stay"),BranchSpec(id="B",name="up",interventions=[InterventionSpec(type="PRICE_CHANGE",tick=1,payload={"price":100})]),BranchSpec(id="C",name="up+incentive",interventions=[InterventionSpec(type="PRICE_CHANGE",tick=1,payload={"price":70}),InterventionSpec(type="INCENTIVE",tick=2,payload={"amount":20})])],source="manual",warnings=["SYNTHETIC_SCENARIO"])
    j = scenario_to_json(s); s2 = scenario_from_json(j); assert s2.id==s.id; assert s2.duration_ticks==s.duration_ticks

def test_fingerprint_deterministic():
    s = ScenarioSpec(id="f",name="x",description="d",initial_state={"price":70},duration_ticks=30,branches=[])
    fp1=scenario_fingerprint(s); fp2=scenario_fingerprint(s); assert fp1==fp2; assert len(fp1)==64

def test_branch_events():
    b=BranchSpec(id="B",name="up",interventions=[InterventionSpec(type="PRICE_CHANGE",tick=1,payload={"price":100})])
    evs=build_branch_events(b); assert len(evs)==1; assert isinstance(evs[0],Event); assert evs[0].type=="PRICE_CHANGE"

def test_initial_state_valid():
    s = ScenarioSpec(id="s",name="x",description="d",initial_state={"price":70},duration_ticks=10,branches=[]); validate_scenario_spec(s)

def test_source_warnings():
    s=ScenarioSpec(id="s",name="x",description="d",initial_state={},duration_ticks=10,branches=[],source="llm_generated",warnings=["UNCALIBRATED_SCENARIO"]); validate_scenario_spec(s)

def test_composition_with_population():
    from futureos.population_spec import PopulationSpec
    p=PopulationSpec(size=8,archetypes=[]); s=ScenarioSpec(id="comp",name="composite",description="d",initial_state={},duration_ticks=5,branches=[]); assert s.source=="manual"

def test_engine_intact():
    from futureos import engine, randomness, models
    assert hasattr(engine,"create_simulation"); assert hasattr(randomness,"SeededRandom")
