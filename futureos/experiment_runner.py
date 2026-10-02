"""M16 Experiment Runner — minimal, reuses existing APIs."""
from __future__ import annotations
import json, hashlib
from pathlib import Path
from copy import deepcopy
from .scenario_builder import scenario_from_json, build_branch_events, apply_initial_state, scenario_fingerprint
from .engine import create_simulation, schedule_event
from .models import World
def run_scenario_experiment(pop_path, scenario_path, seeds=[2026], branch_tick=0, output_dir=None):
    scenario = scenario_from_json(Path(scenario_path).read_text(encoding="utf-8"))
    results=[]
    for seed in seeds:
        world=World(id=f"w-{seed}",agents=[]); apply_initial_state(world,scenario.initial_state)
        sim=create_simulation(f"sim-{scenario.id}-{seed}",seed,world)
        snap_hash=hashlib.sha256(str(sim.world.current_tick).encode()).hexdigest()
        for branch in scenario.branches:
            branch_world=deepcopy(sim.world)
            for ev in build_branch_events(branch):
                sim_b=create_simulation(f"sim-{scenario.id}-{seed}-{branch.id}",seed,branch_world)
                sim_b=schedule_event(sim_b,ev)
                metrics={"events":len(sim_b.world.events),"tick":sim_b.world.current_tick}
            results.append({"seed":seed,"branch_id":branch.id,"snap_hash":snap_hash,"metrics":metrics})
    return {"results":results,"scenario_fingerprint":scenario_fingerprint(scenario)}
