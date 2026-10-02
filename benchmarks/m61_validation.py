"""Fresh-process measurements and stdlib profile for the persisted M6.1 worktree.

Invoke one configuration per process. Product code and hash algorithms are not
changed. The primary timer matches benchmarks.audit; disk output is separate.
"""

import argparse
import cProfile
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import pstats
import sys
from time import perf_counter

from benchmarks.audit import _produced_bytes
from futureos.audit_runs import HASH_FIELDS, run_audit_experiment, save_audit_experiment
from futureos.demo import DEFAULT_SCENARIO
from futureos.experiments import load_experiment_scenario


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def _identity(root, original):
    current = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
               for name in original["runtimeFiles"]}
    if current != original["runtimeFiles"]:
        raise RuntimeError("Product/scenario changed after the suite; revalidate first")
    return original["runtimeManifestSha256"]


def _peak_memory():
    """Windows process high-water marks, including imports; no allocation tracer."""
    if sys.platform != "win32":
        return {"available": False, "reason": "Windows process API required"}

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                   *[(name, ctypes.c_size_t) for name in (
                       "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                       "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                       "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {"available": True, "peakWorkingSetBytes": counters.PeakWorkingSetSize,
            "peakCommitBytes": counters.PeakPagefileUsage,
            "scope": "Process lifetime including imports; Windows resident/commit high-water marks"}


def _rankings(profiler, output):
    profiler.dump_stats(str(output / "profile.pstats"))
    stats = pstats.Stats(profiler)
    rows = []
    for (filename, line, function), (primitive, calls, total, cumulative, _) in stats.stats.items():
        rows.append({"file": filename, "line": line, "function": function,
                     "primitiveCalls": primitive, "calls": calls,
                     "totalSeconds": total, "cumulativeSeconds": cumulative})
    ranking = {key: sorted(rows, key=lambda row: row[field], reverse=True)
               for key, field in (("cumulative", "cumulativeSeconds"),
                                  ("total", "totalSeconds"), ("calls", "calls"))}
    _write(output / "rankings.json", {"totalProfileSeconds": stats.total_tt,
                                      "rankings": ranking,
                                      "warning": "Nested cumulative times overlap; do not add them"})
    for key, field in (("cumulative", "cumtime"), ("total", "tottime"), ("calls", "calls")):
        with (output / f"ranking-{key}.txt").open("w", encoding="utf-8") as stream:
            pstats.Stats(profiler, stream=stream).sort_stats(field).print_stats(40)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("measure", "profile"))
    parser.add_argument("--ticks", required=True, type=int)
    parser.add_argument("--mode", choices=("summary", "trace"), default="trace")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path.cwd()
    baseline = json.loads((args.output / "code-identity.json").read_text(encoding="utf-8"))
    digest = _identity(root, baseline)
    name = (f"ticks-{args.ticks}-{args.mode}-run-{args.repeat}" if args.action == "measure"
            else f"profile-{args.ticks}-{args.mode}")
    output = args.output / name
    output.mkdir(exist_ok=False)
    scenario = load_experiment_scenario(DEFAULT_SCENARIO)
    started_at = datetime.now(timezone.utc).isoformat()
    profiler = cProfile.Profile() if args.action == "profile" else None
    if profiler:
        profiler.enable()
    start = perf_counter()
    result = run_audit_experiment(scenario, [2026], ticks=args.ticks, mode=args.mode)
    execution_seconds = perf_counter() - start
    start = perf_counter()
    size = _produced_bytes(result)
    serialization_seconds = perf_counter() - start
    seconds = execution_seconds + serialization_seconds
    memory_before_disk = _peak_memory()
    start = perf_counter()
    save_audit_experiment(result, output / "artifacts")
    disk_seconds = perf_counter() - start
    if profiler:
        profiler.disable()
    memory = _peak_memory()
    actual_size = sum(path.stat().st_size for path in (output / "artifacts").rglob("*.json"))
    if size != actual_size:
        raise RuntimeError(f"Serialized bytes {size} differ from disk bytes {actual_size}")
    branch_count = len(result.runs)
    origin_ticks = scenario["initial_ticks"]
    physical_ticks = origin_ticks + branch_count * (args.ticks - origin_ticks)
    interactions = sum(run["metrics"]["interaction_count"] for run in result.runs)
    origin_interactions = result.runs[0]["frames"][origin_ticks - 1]["metrics"]["interaction_count"]
    physical_interactions = interactions - (branch_count - 1) * origin_interactions
    summary = {"measurementVersion": 1, "action": args.action, "startedAtUtc": started_at,
               "finishedAtUtc": datetime.now(timezone.utc).isoformat(), "ticks": args.ticks,
               "mode": args.mode, "repeat": args.repeat, "seed": 2026,
               "scenario": scenario["id"], "population": scenario["population_size"],
               "pythonVersion": platform.python_version(), "processId": __import__("os").getpid(),
               "runtimeManifestSha256": digest, "seconds": seconds,
               "executionSeconds": execution_seconds, "artifactSerializationSeconds": serialization_seconds,
               "diskOutputSeconds": disk_seconds, "physicalTicks": physical_ticks,
               "secondsPerPhysicalTick": seconds / physical_ticks, "bytesProduced": size,
               "actualDiskBytes": actual_size, "runCount": branch_count,
               "traceRecordsStored": sum(len(run["records"]) for run in result.runs),
               "traceCountExported": sum(run["traceCount"] for run in result.runs),
               "framesStored": sum(len(run["frames"]) for run in result.runs),
               "interactionsExported": interactions, "physicalInteractions": physical_interactions,
               "peakMemoryBeforeDisk": memory_before_disk, "peakMemoryIncludingDisk": memory,
               "hashes": [{"branchId": run["branchId"], "runId": run["runId"],
                           **{key: run[key] for key in HASH_FIELDS}} for run in result.runs],
               "timingScope": "Preflight, simulation, reports, canonical artifact sizing; excludes disk output",
               "diskScope": "save_audit_experiment including validation, repeated serialization and writes",
               "instrumented": profiler is not None}
    _write(output / "measurement.json", summary)
    if profiler:
        _rankings(profiler, output)
    print(json.dumps({key: summary[key] for key in ("ticks", "mode", "repeat", "seconds",
                     "diskOutputSeconds", "bytesProduced", "traceRecordsStored", "physicalInteractions")},
                     sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
