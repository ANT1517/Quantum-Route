"""Solver dispatch for Person B's code paths (run_job, fleet loop, re-routing).

Until Person A's `solver` branch is merged, QPSO is not available here, so every request falls back to
the OR-Tools stand-in (`standin.py`). After the merge, `algorithm="qpso"` (and the other metaheuristics)
automatically use A's real optimizers through the frozen Optimizer protocol (§5.2).
The returned dict always says which algorithm actually ran.
"""
import time

import numpy as np

from qflux.types import Instance, Refs, Weights


def _real_optimizer(algorithm: str):
    """A's optimizer + Evaluator, or None if the solver branch is not merged yet."""
    try:
        from qflux.core.evaluate import Evaluator
        mod = __import__(f"qflux.algos.{algorithm}", fromlist=["*"])
    except ImportError:
        return None
    cls = next((getattr(mod, n) for n in dir(mod)
                if isinstance(getattr(mod, n), type) and getattr(getattr(mod, n), "name", None) == algorithm), None)
    return (cls, Evaluator) if cls else None


def solve(inst: Instance, w: Weights, refs: Refs, *, algorithm: str = "qpso", seed: int = 0,
          budget: dict | None = None, params: dict | None = None, warm_start_perm=None,
          warm_start_routes=None, progress=None, should_stop=None) -> dict:
    """Returns {"routes", "algorithm", "evals", "convergence", "partial", "perm"}."""
    budget = budget or {}
    real = None if algorithm == "ortools" else _real_optimizer(algorithm)
    if real is not None:
        from qflux.core.encoding import encode_perm
        from qflux.rng import make_rng
        cls, Evaluator = real
        ev = Evaluator(inst, w, refs)
        rng = make_rng(seed)
        init_keys = None
        if warm_start_perm is not None:
            init_keys = encode_perm(np.asarray(warm_start_perm), rng)
        opt = cls(**(params or {})) if params else cls()
        t = time.time()
        sol, curve = opt.run(ev, budget.get("evals"), budget.get("time_s"), rng, callback=progress,
                             should_stop=should_stop, init_keys=init_keys)
        conv = [dict(iter=k, evals=int(e), best_F=float(f)) for k, (e, f) in enumerate(curve)]
        return dict(routes=[list(map(int, r)) for r in sol.routes], algorithm=algorithm, evals=ev.evals,
                    convergence=conv, partial=bool(sol.meta.get("partial", False)), perm=list(map(int, sol.perm)),
                    wall_s=time.time() - t)

    from .standin import solve_ortools
    if warm_start_routes is None and warm_start_perm is not None:
        warm_start_routes = None   # a giant tour alone is not a route set; OR-Tools restarts cold
    time_s = float(budget.get("time_s") or 5.0)
    return solve_ortools(inst, w, refs, time_limit_s=time_s, warm_start_routes=warm_start_routes,
                         progress=progress, requested=algorithm)
