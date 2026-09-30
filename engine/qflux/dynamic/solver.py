"""Solver dispatch for Person B's code paths (run_job, fleet loop, re-routing).

When Person A's engine is present (`qflux.algos.registry.get_optimizer`), metaheuristics run through it
with A's Evaluator (frozen Optimizer protocol, §5.2). Otherwise — and always for algorithm="ortools" —
the OR-Tools stand-in (`standin.py`) runs. The returned dict always says which algorithm actually ran.
"""
import time

import numpy as np

from qflux.config import load_config
from qflux.types import Instance, Refs, Weights


def engine_available() -> bool:
    try:
        import qflux.algos.registry  # noqa: F401
        import qflux.core.evaluate  # noqa: F401
    except ImportError:
        return False
    return True


def _map_params(algorithm: str, params: dict) -> dict:
    """UI params {N, iterations, alpha_start, alpha_end} -> optimizer params; unknown keys dropped."""
    out = {}
    if "N" in params:
        out["N" if algorithm.startswith(("qpso", "pso", "sa")) else "pop"] = int(params["N"])
    if algorithm.startswith("qpso"):
        if "alpha_start" in params:
            out["alpha_max"] = float(params["alpha_start"])
        if "alpha_end" in params:
            out["alpha_min"] = float(params["alpha_end"])
        for k in ("alpha_mode", "alpha_max", "alpha_min", "alpha_fixed", "mbest", "init", "ls_every", "tunneling",
                  "qubo_slot"):
            if k in params:
                out[k] = params[k]
    return out


def _warm_up_jit(ev) -> None:
    """Trigger Numba compilation of Split and LS without counting evaluations (first call can take ~5 s)."""
    from qflux.core.localsearch import improve_routes
    perm = np.arange(1, ev.inst.n + 1)
    sol = ev.solution(perm)
    improve_routes(sol.routes[:2], ev, max_rounds=1)


def solve(inst: Instance, w: Weights, refs: Refs, *, algorithm: str = "qpso", seed: int = 0,
          budget: dict | None = None, params: dict | None = None, warm_start_perm=None,
          warm_start_routes=None, progress=None, should_stop=None) -> dict:
    """Returns {"routes", "algorithm", "evals", "convergence", "partial", "perm", "wall_s"}."""
    budget = dict(budget or {})
    params = dict(params or {})
    if algorithm != "ortools" and engine_available():
        from qflux.algos.registry import get_optimizer
        from qflux.core.encoding import encode_perm
        from qflux.core.evaluate import Evaluator
        from qflux.rng import make_rng
        if budget.get("evals") is None and budget.get("time_s") is None:
            budget["evals"] = load_config()["budget"]["evals"]
        if budget.get("evals") is None and "N" in params and "iterations" in params:
            budget["evals"] = int(params["N"]) * int(params["iterations"])
        ev = Evaluator(inst, w, refs)
        _warm_up_jit(ev)                       # Numba compile time must not eat a time budget
        rng = make_rng(seed)
        init_keys = None if warm_start_perm is None else encode_perm(np.asarray(warm_start_perm), rng)
        opt = get_optimizer(algorithm, _map_params(algorithm, params))
        t = time.time()
        sol, curve = opt.run(ev, budget.get("evals"), budget.get("time_s"), rng, callback=progress,
                             should_stop=should_stop, init_keys=init_keys)
        conv = [dict(iter=k, evals=int(e), best_F=float(f)) for k, (e, f) in enumerate(curve)]
        return dict(routes=[list(map(int, r)) for r in sol.routes], algorithm=getattr(opt, "name", algorithm),
                    evals=ev.evals, convergence=conv, partial=bool(sol.meta.get("partial", False)),
                    perm=list(map(int, sol.perm)), wall_s=time.time() - t)

    from .standin import solve_ortools
    time_s = float(budget.get("time_s") or 5.0)
    return solve_ortools(inst, w, refs, time_limit_s=time_s, warm_start_routes=warm_start_routes,
                         progress=progress, requested=algorithm)
