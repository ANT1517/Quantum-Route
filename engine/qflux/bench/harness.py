"""Benchmark harness (§9 Phase 2, §11): one RunRecord JSON line per (algorithm, instance, seed, budget).

- seed = seed_base + 1000 * instance_idx + run_idx, with instance_idx taken from the fixed §11.1 order
  (INSTANCE_ORDER), so the same instance gets the same seeds in every experiment and every algorithm
  sees the same seeds (paired comparisons).
- Budget modes: "evals" (full evaluations) and "time" (wall-clock seconds, single process).
- Every solution goes through the independent feasibility checker; failures are written to
  <exp>.infeasible.jsonl and never to the main file, so "0 infeasible in N runs" can be counted.
- Re-running an experiment skips records that already exist (resume after an interruption).
- Parallel execution (D30): up to (physical cores - 1) worker processes, each pinned to one thread
  (NUMBA_NUM_THREADS=1, OMP_NUM_THREADS=1), so time-budget runs do not compete for CPU.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

import numpy as np
import yaml

from qflux.algos.registry import get_optimizer
from qflux.bench.loader import load_instance
from qflux.config import REPO_ROOT, load_config
from qflux.core.evaluate import Evaluator
from qflux.core.feasibility import check
from qflux.rng import make_rng
from qflux.types import RunRecord, Weights

EXP_DIR = REPO_ROOT / "configs" / "experiments"
RUNS_DIR = REPO_ROOT / "results" / "runs"

# §11.1 order; fixes instance_idx in the seed formula.
INSTANCE_ORDER = ["P-n16-k8", "P-n19-k2", "P-n22-k8", "A-n32-k5", "A-n44-k6", "A-n63-k9", "A-n80-k10",
                  "CMT1", "CMT5", "X-n101-k25", "X-n200-k36", "X-n502-k39", "X-n1001-k43",
                  "A-n69-k9"]                          # appended (D35), so earlier seeds are unchanged
CURVE_STEP = 100
SUSPEND_FACTOR = 1.10        # a time-budget run longer than this x budget was suspended (sleep) or hit a clock jump
META_KEYS = ("iterations", "moves", "partial", "ls_calls", "qubo_calls", "qubo_improvements", "qubo_skipped_time",
             "reinits", "solutions_found", "max_abs_key", "curve_t")
THREAD_ENV = {"NUMBA_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
              "OPENBLAS_NUM_THREADS": "1"}


def physical_cores() -> int:
    try:
        import psutil
        n = psutil.cpu_count(logical=False)
        if n:
            return int(n)
    except ImportError:
        pass
    if sys.platform == "win32":
        try:
            out = subprocess.run(["powershell", "-NoProfile", "-Command",
                                  "(Get-CimInstance Win32_Processor | Measure-Object NumberOfCores -Sum).Sum"],
                                 capture_output=True, text=True, timeout=20).stdout.strip()
            return int(out)
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    return max(1, (os.cpu_count() or 2) // 2)


def default_workers() -> int:
    return max(1, physical_cores() - 1)


def load_experiment(name_or_path: str) -> dict:
    p = Path(name_or_path)
    if not p.suffix:
        p = EXP_DIR / f"{name_or_path}.yaml"
    with open(p, encoding="utf-8") as f:
        exp = yaml.safe_load(f)
    exp.setdefault("name", p.stem)
    return exp


def run_seed(instance: str, run_idx: int, seed_base: int | None = None) -> int:
    if seed_base is None:
        seed_base = int(load_config()["seed_base"])
    if instance in INSTANCE_ORDER:
        idx = INSTANCE_ORDER.index(instance)
    else:                                   # instances outside §11.1: stable index from the name
        idx = 100 + int(hashlib.sha1(instance.encode()).hexdigest(), 16) % 900
    return seed_base + 1000 * idx + run_idx


def config_hash(algo: str, params: dict, weights: Weights, budget_type: str, budget: float) -> str:
    blob = json.dumps({"algo": algo, "params": params, "weights": asdict(weights),
                       "budget_type": budget_type, "budget": budget}, sort_keys=True, default=_jsonable)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def _jsonable(x):
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, np.ndarray):
        return x.tolist()
    return str(x)


def resample_curve(curve, evals_used: int, final_F: float, step: int = CURVE_STEP) -> list[tuple[int, float]]:
    """(evals, best_F) every `step` evaluations (best-so-far, step function) plus the final point."""
    pts = sorted((int(e), float(f)) for e, f in curve)
    out: list[tuple[int, float]] = []
    best, k = np.inf, 0
    for g in range(step, evals_used + 1, step):
        while k < len(pts) and pts[k][0] <= g:
            best = min(best, pts[k][1])
            k += 1
        if np.isfinite(best):
            out.append((g, best))
    best = min([best] + [f for _, f in pts[k:]] + [final_F])
    if not out or out[-1][0] != evals_used:
        out.append((int(evals_used), float(best)))
    return out


def single_run(inst, algo: str, params: dict, weights: Weights, budget_type: str, budget: float, seed: int,
               label: str | None = None):
    """One run -> (RunRecord, feasible, errors). `label` names a variant (RunRecord.algo); default = algo."""
    ev = Evaluator(inst, weights)
    opt = get_optimizer(algo, params)
    t = time.time()
    sol, curve = opt.run(ev, int(budget) if budget_type == "evals" else None,
                         float(budget) if budget_type == "time" else None, make_rng(seed))
    wall = time.time() - t
    ok, errs = check(inst, sol, ev)
    gap = None
    fleet_excess = max(0, sol.n_vehicles - inst.K) if inst.K is not None else 0
    if inst.bks and fleet_excess == 0:   # convention matches the BKS (§11.2); m > K: no gap (D38)
        gap = 100.0 * (sol.D - inst.bks) / inst.bks
    eff = getattr(opt, "p", params)
    meta = {k: sol.meta[k] for k in META_KEYS if k in sol.meta}
    meta["tunnel_events"] = len(sol.meta.get("tunnel_events", []))
    meta["fleet_excess"] = fleet_excess                                                    # D38
    rec = RunRecord(algo=label or algo, instance=inst.name, seed=seed, budget_type=budget_type, budget=float(budget),
                    best_F=float(sol.F), best_T=float(sol.T), best_D=float(sol.D), best_C=float(sol.C),
                    best_E=float(sol.E), n_vehicles=int(sol.n_vehicles), gap_pct=gap, evals_used=int(ev.evals),
                    wall_s=float(wall), curve=resample_curve(curve, int(ev.evals), float(sol.F)),
                    config_hash=config_hash(algo, eff, weights, budget_type, budget), meta=meta)
    return rec, ok, errs


def _key(d) -> tuple:
    return (d["algo"], d["instance"], int(d["seed"]), d["budget_type"], float(d["budget"]))


def read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def plan(exp: dict) -> list[tuple]:
    """[(instance, algo, budget_type, budget, run_idx, seed)] in a stable order."""
    runs = int(exp.get("runs", 3))
    jobs = []
    for b in exp["budgets"]:
        for inst in b.get("instances", exp["instances"]):          # a budget may name its own instances
            for r in range(runs):
                seed = run_seed(inst, r, exp.get("seed_base"))
                for algo in b["algorithms"]:
                    jobs.append((inst, algo, b["type"], float(b["value"]), r, seed))
    return jobs


def warm_up(algos, inst_name: str):
    """Compile / load Numba kernels before any timed run (wall times must not include JIT)."""
    inst = load_instance(inst_name)
    for a in dict.fromkeys(algos):
        if a == "ortools":
            from ortools.constraint_solver import pywrapcp  # noqa: F401  (one-time import kept out of timed runs)
            continue
        if a == "nn":
            continue
        get_optimizer(a).run(Evaluator(inst, Weights(wT=0, wD=1)), 200, None, make_rng(0))


_INST_CACHE: dict = {}


def _worker_init(algos, inst_name):
    os.environ.update(THREAD_ENV)
    warm_up(algos, inst_name)


def _job(iname, label, algo, params, w, btype, budget, seed):
    if iname not in _INST_CACHE:
        _INST_CACHE.clear()                         # one instance in memory per process
        _INST_CACHE[iname] = load_instance(iname)
    rec, ok, errs = single_run(_INST_CACHE[iname], algo, params, w, btype, budget, seed, label)
    return asdict(rec), ok, errs


def run_experiment(exp: dict, out_dir: Path | None = None, log=print, workers: int | None = None) -> Path:
    out_dir = Path(out_dir or RUNS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{exp['name']}.jsonl"
    bad_path = out_dir / f"{exp['name']}.infeasible.jsonl"
    done = {_key(d) for d in read_records(path)} | {_key(d) for d in read_records(bad_path)}
    w = Weights(*exp.get("weights", [0.0, 1.0, 0.0, 0.0]))
    params = exp.get("params", {}) or {}
    jobs = [j for j in plan(exp) if (j[1], j[0], j[5], j[2], j[3]) not in done]
    workers = int(workers or exp.get("workers") or default_workers())
    workers = max(1, min(workers, len(jobs) or 1))
    log(f"[{exp['name']}] {len(jobs)} runs to do ({len(done)} already recorded), {workers} worker(s) -> {path}")
    if not jobs:
        return path
    variants = exp.get("variants", {}) or {}         # label -> {algo, params}: several configs of one algorithm

    def resolve(label):
        v = variants.get(label)
        return (v["algo"], dict(v.get("params", {}) or {})) if v else (label, dict(params.get(label, {}) or {}))

    algos = [resolve(j[1])[0] for j in jobs]
    t_all = time.time()
    n_done = 0

    invalid_path = out_dir / f"{exp['name']}.invalid.jsonl"

    def record(rd, ok, errs):
        nonlocal n_done
        n_done += 1
        if rd["budget_type"] == "time" and rd["wall_s"] > SUSPEND_FACTOR * rd["budget"]:
            # machine sleep / clock jump: the run did not get a fair budget. Not recorded as done, so a
            # resume re-runs it; kept in <exp>.invalid.jsonl for the record.
            with open(invalid_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({**rd, "invalid_reason": f"wall {rd['wall_s']:.1f} s > {SUSPEND_FACTOR} x budget"},
                                   default=_jsonable) + "\n")
            log(f"  [{n_done}/{len(jobs)}] {rd['instance']} {rd['algo']} seed={rd['seed']}: INVALID "
                f"(wall {rd['wall_s']:.1f} s on a {rd['budget']:g} s budget; suspended?) -> will re-run on resume")
            return
        if ok:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rd, default=_jsonable) + "\n")
        else:
            with open(bad_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({**rd, "errors": errs}, default=_jsonable) + "\n")
        gap = "n/a" if rd["gap_pct"] is None else f"{rd['gap_pct']:.2f}%"
        log(f"  [{n_done}/{len(jobs)}] {rd['instance']} {rd['algo']} {rd['budget_type']}={rd['budget']:g} "
            f"seed={rd['seed']}: D={rd['best_D']:.1f} gap={gap} evals={rd['evals_used']} {rd['wall_s']:.2f}s "
            f"ls={rd['meta'].get('ls_calls', 0)}{'' if ok else '  INFEASIBLE ' + '; '.join(errs)}")

    args = [(iname, label, *resolve(label), w, btype, budget, seed)
            for (iname, label, btype, budget, r, seed) in jobs]
    if workers == 1:
        warm_up(algos, jobs[0][0])
        for a in args:
            record(*_job(*a))
    else:
        saved = {k: os.environ.get(k) for k in THREAD_ENV}
        os.environ.update(THREAD_ENV)               # inherited by the spawned workers
        try:
            with ProcessPoolExecutor(max_workers=workers, initializer=_worker_init,
                                     initargs=(algos, jobs[0][0])) as pool:
                futs = [pool.submit(_job, *a) for a in args]
                for fut in as_completed(futs):
                    record(*fut.result())
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    log(f"[{exp['name']}] done in {time.time() - t_all:.0f} s")
    return path
