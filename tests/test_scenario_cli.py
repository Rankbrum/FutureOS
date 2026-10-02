"""M15.1 CLI scenario tests."""
import subprocess,sys,json
from pathlib import Path
FIXTURE=Path("fixtures/pricing_scenario.json")
def _run(cmd): return subprocess.run([sys.executable,"-m","futureos"]+cmd,capture_output=True,text=True)
def test_validate_valid(): r=_run(["scenario","validate","--spec",str(FIXTURE)]); assert r.returncode==0; assert "VALID" in r.stdout; assert "FINGERPRINT" in r.stdout
def test_show(): r=_run(["scenario","show","--spec",str(FIXTURE)]); assert r.returncode==0; assert "id:" in r.stdout or "name:" in r.stdout
def test_file_missing(): r=_run(["scenario","validate","--spec","no.json"]); assert r.returncode!=0
