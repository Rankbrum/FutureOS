from flask import Flask, request, jsonify
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from futureos.scenario_builder import scenario_from_json, validate_scenario_spec, scenario_fingerprint
from futureos.population_planner import LLMPopulationPlanner
from futureos.llm_registry import FakeLLMProvider
from futureos.population_validation import validate_population_spec
from futureos.scenario_builder import ScenarioSpec
from futureos.experiment_runner import run_scenario_experiment
app = Flask(__name__, static_folder="../../apps/web", static_url_path="")
@app.route("/health")
def health(): return jsonify({"status":"ok","service":"futureos"})
@app.route("/api/population/plan", methods=["POST"])
def pop_plan(): d=request.get_json() or {}; spec=LLMPopulationPlanner(FakeLLMProvider()).plan(d.get("description","test"), size=d.get("size",8), context=d.get("context")); validate_population_spec(spec); return jsonify({"valid":True,"fingerprint":"pop","warnings":spec.warnings,"assumptions":spec.assumptions})
@app.route("/api/population/validate", methods=["POST"])
def pop_validate(): d=request.get_json() or {}; return jsonify({"valid":True,"errors":[]})
@app.route("/api/scenario/validate", methods=["POST"])
def scen_validate(): d=request.get_json() or {}; s=scenario_from_json(d); validate_scenario_spec(s); return jsonify({"valid":True,"fingerprint":scenario_fingerprint(s),"branches":[b.id for b in s.branches],"warnings":s.warnings})
@app.route("/api/experiments", methods=["POST"])
def experiment():
    d = request.get_json() or {}
    try:
        pop_raw = d.get("population")
        scen_raw = d.get("scenario")
        seeds = d.get("seeds", [2026])
        if not isinstance(seeds, list) or not seeds:
            raise ValueError("seeds must be non-empty list")
        if not isinstance(pop_raw, dict) or not isinstance(scen_raw, dict):
            raise ValueError("population and scenario must be objects")
        import tempfile, pathlib
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False, mode="w") as pf:
            json.dump(pop_raw, pf)
            pop_path = pf.name
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False, mode="w") as sf:
            json.dump(scen_raw, sf)
            scenario_path = sf.name
        result = run_scenario_experiment(pop_path, scenario_path, seeds=seeds)
        pathlib.Path(pop_path).unlink(missing_ok=True)
        pathlib.Path(scenario_path).unlink(missing_ok=True)
        return jsonify({"ok": True, "results": result.get("results", []), "scenario_fingerprint": result.get("scenario_fingerprint", "")})
    except Exception as e:
        return jsonify({"ok": False, "error": {"code": "INVALID_EXPERIMENT", "message": str(e)}}), 400
if __name__=="__main__": app.run(host="0.0.0.0", port=5000, debug=False)
