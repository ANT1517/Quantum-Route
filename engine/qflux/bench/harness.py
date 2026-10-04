"""Benchmark harness (§9 Phase 2, §11): one RunRecord JSON line per (algorithm, instance, seed, budget).

- seed = seed_base + 1000 * instance_idx + run_idx, with instance_idx taken from the fixed §11.1 order
  (INSTANCE_ORDER), so the same instance gets the same seeds in every experiment and every algorithm
  sees the same seeds (paired comparisons).
- Budget modes: "evals" (full evaluations) and "time" (wall-clock seconds, single process).
- Every solution goes through the independent feasibility checker; failures are written to
  <exp>.infeasible.jsonl and never to the main file, so "0 infeasible in N runs" can be counted.
- Re-running an experiment skips records that already exist (resume after an interruption).
"""
import hashlib
import json
import time
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
                  "CMT1", "CMT5", "X-n101-k25", "X-n200-k36", "X-n502-k39", "X-n1001-k43"]
CURVE_STEP = 100
META_KEYS = ("iterations", "moves", "partial", "ls_calls", "qubo_calls", "qubo_improvements", "qubo_skipped_time",
             "reinits", "solutions_found")


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


def single_run(inst, algo: str, params: dict, weights: Weights, budget_type: str, budget: float, seed: int):
    """One run -> (RunRecord, feasible, errors)."""
    ev = Evaluator(inst, weights)
    opt = get_optimizer(algo, params)
    t = time.time()
    sol, curve = opt.run(ev, int(budget) if budget_type == "evals" else None,
                         float(budget) if budget_type == "time" else None, make_rng(seed))
    wall = time.time() - t
    ok, errs = check(inst, sol, ev)
    gap = None
    if inst.bks:                     # our distance convention always matches the BKS one (§11.2)
        gap = 100.0 * (sol.D - inst.bks) / inst.bks
    eff = getattr(opt, "p", params)
    meta = {k: sol.meta[k] for k in META_KEYS if k in sol.meta}
    meta["tunnel_events"] = len(sol.meta.get("tunnel_events", []))
    rec = RunRecord(algo=algo, instance=inst.name, seed=seed, budget_type=budget_type, budget=float(budget),
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
        for inst in exp["instances"]:
            for r in range(runs):
                seed = run_seed(inst, r, exp.get("seed_base"))
                for algo in b["algorithms"]:
                    jobs.append((inst, algo, b["type"], float(b["value"]), r, seed))
    return jobs


def warm_up(algos, inst_name: str):
    """Compile Numba kernels before any timed run (wall times must not include JIT)."""
    inst = load_instance(inst_name)
    for a in dict.fromkeys(algos):
        if a in ("ortools", "nn"):
            continue
        get_optimizer(a).run(Evaluator(inst, Weights(wT=0, wD=1)), 200, None, make_rng(0))


def run_experiment(exp: dict, out_dir: Path | None = None, log=print) -> Path:
    out_dir = Path(out_dir or RUNS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{exp['name']}.jsonl"
    bad_path = out_dir / f"{exp['name']}.infeasible.jsonl"
    done = {_key(d) for d in read_records(path)} | {_key(d) for d in read_records(bad_path)}
    w = Weights(*exp.get("weights", [0.0, 1.0, 0.0, 0.0]))
    params = exp.get("params", {}) or {}
    jobs = [j for j in plan(exp) if (j[1], j[0], j[5], j[2], j[3]) not in done]
    log(f"[{exp['name']}] {len(jobs)} runs to do ({len(done)} already recorded) -> {path}")
    if not jobs:
        return path
    warm_up([j[1] for j in jobs], jobs[0][0])
    cache: dict = {}
    t_all = time.time()
    for k, (iname, algo, btype, budget, r, seed) in enumerate(jobs, 1):
        if iname not in cache:
            cache = {iname: load_instance(iname)}       # one instance in memory at a time
        rec, ok, errs = single_run(cache[iname], algo, dict(params.get(algo, {})), w, btype, budget, seed)
        line = json.dumps(asdict(rec), default=_jsonable)
        if ok:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        else:
            with open(bad_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({**asdict(rec), "errors": errs}, default=_jsonable) + "\n")
        gap = "n/a" if rec.gap_pct is None else f"{rec.gap_pct:.2f}%"
        log(f"  [{k}/{len(jobs)}] {iname} {algo} {btype}={budget:g} seed={seed}: D={rec.best_D:.1f} "
            f"gap={gap} evals={rec.evals_used} {rec.wall_s:.1f}s{'' if ok else '  INFEASIBLE ' + '; '.join(errs)}")
    log(f"[{exp['name']}] done in {time.time() - t_all:.0f} s")
    return path
