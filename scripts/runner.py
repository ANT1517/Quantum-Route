"""Standalone experiment runner (D51). Start it in its own terminal (not as a child task of an agent shell):

    powershell: Start-Process -FilePath <venv python> -ArgumentList "scripts/runner.py --phase main" `
                -WorkingDirectory <repo> -WindowStyle Minimized
Stop it (whole process tree) with:  powershell -File scripts/stop_runner.ps1

- PID/lock file results/run_info/runner.lock (refuses to start if another runner is alive).
- Refuses to start with < 4 GB free; logs free memory every 60 s to results/run_info/mem_log.csv.
- Before each step waits until >= 2 GB is free; inside benchmark steps the harness also pauses new runs
  below 2 GB (QR_MIN_FREE_GB). Stops at the first failing step. Status: results/run_info/runner_status.json.
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

from qflux.bench.harness import free_memory_gb, keep_awake  # noqa: E402

INFO = ROOT / "results" / "run_info"
LOGS = ROOT / "results" / "logs"
LOCK = INFO / "runner.lock"
PY = sys.executable
START_MIN_GB, PAUSE_MIN_GB = 4.0, 2.0

PHASES = {
    # 4a-4d of the 2026-10-04 plan
    "main": [
        ("d51_rerun_bench_core_v1", [PY, "-u", "scripts/run_bench.py", "--exp", "bench_core_v1"]),
        ("d51_rerun_ablation", [PY, "-u", "scripts/run_bench.py", "--exp", "ablation"]),
        ("d51_rerun_alpha_sweep", [PY, "-u", "scripts/run_bench.py", "--exp", "alpha_sweep"]),
        ("d51_audit_after", [PY, "scripts/audit_throughput.py", "--no-arrivals", "--out", "d51_audit_after"]),
        ("milp_parallel", [PY, "-u", "scripts/run_milp.py", "--time-limit", "600", "--jobs", "3"]),
        ("qubo_check", [PY, "-u", "scripts/run_qubo_check.py"]),
        ("api_job_tests", [PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/api"]),
    ],
    # D51 second (final) pass: re-run the runs the post-rerun audit still flags, then audit once more
    "d51_pass2": [
        ("d51_pass2_move", [PY, "scripts/d51_replace.py", "--audit", "d51_audit_after"]),
        ("d51_pass2_bench_core_v1", [PY, "-u", "scripts/run_bench.py", "--exp", "bench_core_v1"]),
        ("d51_pass2_ablation", [PY, "-u", "scripts/run_bench.py", "--exp", "ablation"]),
        ("d51_audit_final", [PY, "scripts/audit_throughput.py", "--no-arrivals", "--out", "d51_audit_final"]),
    ],
    # after the 16:21 CBC hang (-threads 1, fixed) and the 16:37-17:01 standby: D51 pass 2, then 4b-4d
    "resume": [
        ("d51_pass2_move", [PY, "scripts/d51_replace.py", "--audit", "d51_audit_after"]),
        ("d51_pass2_bench_core_v1", [PY, "-u", "scripts/run_bench.py", "--exp", "bench_core_v1"]),
        ("d51_pass2_ablation", [PY, "-u", "scripts/run_bench.py", "--exp", "ablation"]),
        ("d51_audit_final", [PY, "scripts/audit_throughput.py", "--no-arrivals", "--out", "d51_audit_final"]),
        ("milp_parallel", [PY, "-u", "scripts/run_milp.py", "--time-limit", "600", "--jobs", "3"]),
        ("qubo_check", [PY, "-u", "scripts/run_qubo_check.py"]),
        ("api_job_tests", [PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/api"]),
    ],
    # D55: OR-Tools re-run with the matrix API (only its rows), then the P-instance heuristic-vs-exact run
    "d55": [
        ("d55_move_bench_core_v1", [PY, "scripts/supersede_rows.py", "--exp", "bench_core_v1", "--algos", "ortools", "--tag", "d55"]),
        ("d55_move_scaling", [PY, "scripts/supersede_rows.py", "--exp", "scaling", "--algos", "ortools", "--tag", "d55"]),
        ("d55_rerun_bench_core_v1", [PY, "-u", "scripts/run_bench.py", "--exp", "bench_core_v1"]),
        ("d55_rerun_scaling", [PY, "-u", "scripts/run_bench.py", "--exp", "scaling"]),
        ("p_small", [PY, "-u", "scripts/run_bench.py", "--exp", "p_small"]),
    ],
    # D54 confirmatory round: tuning (tuning instances only), then (after the committed choice) confirmation
    "d54_tune": [("tune_d54", [PY, "-u", "scripts/run_bench.py", "--exp", "tune_d54"])],
    "d54_confirm": [("confirm_d54", [PY, "-u", "scripts/run_bench.py", "--exp", "confirm_d54"])],
    # optional, after D46: nothing else may run during the P-core check
    "optional": [
        ("pcore_check", [PY, "-u", "scripts/run_bench.py", "--exp", "pcore_check"]),
        ("profile_qpso", [PY, "scripts/profile_qpso.py", "--instance", "A-n80-k10", "--time-s", "30"]),
    ],
}


def pid_alive(pid: int) -> bool:
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
    return str(pid) in out


class State:
    step = "starting"


def mem_logger(stop: threading.Event):
    path = INFO / "mem_log.csv"
    new = not path.exists()
    with open(path, "a", encoding="utf-8") as f:
        if new:
            f.write("time,free_gb,step\n")
        while not stop.is_set():
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')},{free_memory_gb():.2f},{State.step}\n")
            f.flush()
            stop.wait(60)


def status(**kw):
    (INFO / "runner_status.json").write_text(json.dumps({"pid": os.getpid(), "time": time.strftime("%H:%M:%S"), **kw},
                                                        indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=sorted(PHASES), default="main")
    a = ap.parse_args()
    INFO.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        other = int(LOCK.read_text().strip() or 0)
        if other and pid_alive(other):
            sys.exit(f"another runner (PID {other}) is alive; lock {LOCK}")
    free = free_memory_gb()
    if free is not None and free < START_MIN_GB:
        sys.exit(f"only {free:.1f} GB free (< {START_MIN_GB:g} GB); close applications and retry")
    LOCK.write_text(str(os.getpid()))
    keep_awake(True)                                  # whole runner lifetime (not only benchmark steps)
    stop = threading.Event()
    threading.Thread(target=mem_logger, args=(stop,), daemon=True).start()
    env = dict(os.environ, PYTHONPATH=str(ROOT / "engine"), QR_MIN_FREE_GB=str(PAUSE_MIN_GB), PYTHONUNBUFFERED="1")
    try:
        for name, cmd in PHASES[a.phase]:
            State.step = name
            while (free_memory_gb() or 99) < PAUSE_MIN_GB:
                status(step=name, state="paused (low memory)", free_gb=free_memory_gb())
                time.sleep(15)
            status(step=name, state="running", started=time.strftime("%H:%M:%S"))
            with open(LOGS / "queue.log", "a", encoding="utf-8") as q:
                q.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} runner[{a.phase}] start {name}\n")
            with open(LOGS / f"{name}.log", "w", encoding="utf-8") as log:
                rc = subprocess.call(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            with open(LOGS / "queue.log", "a", encoding="utf-8") as q:
                q.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} runner[{a.phase}] done {name} rc={rc}\n")
            if rc != 0:
                status(step=name, state=f"FAILED rc={rc}")
                return rc
        State.step = "finished"
        status(step=None, state=f"phase {a.phase} finished")
        return 0
    finally:
        stop.set()
        keep_awake(False)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    sys.exit(main())
