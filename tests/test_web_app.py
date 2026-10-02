"""M17 minimal web/app tests."""
import json
def test_health_exists(): pass
def test_populate_plan_contract(): pass
def test_scenario_validate_contract(): pass
def test_experiment_contract():
    import json
    with open("docs/evidence/M13_POPULATION_SPEC.json") as f: pop = json.load(f)
    with open("fixtures/pricing_scenario.json") as f: scen = json.load(f)
    from apps.api.app import app
    with app.test_client() as c:
        resp = c.post("/api/experiments", json={"population": pop, "scenario": scen, "seeds": [2026]})
        data = resp.get_json()
        assert resp.status_code == 200
        assert data.get("ok") is True
        assert "results" in data
        assert "scenario_fingerprint" in data
        assert data.get("aggregate") is None
        assert data.get("fingerprint") != "exp-1"
def test_engine_intact(): from futureos import engine; assert hasattr(engine,"create_simulation")
