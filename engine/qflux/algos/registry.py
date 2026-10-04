"""get_optimizer(name, params): the one place that maps algorithm names to Optimizer objects (§5.2).

Names: qpso, qpso_base, pso, pso_ls, ga, ga_ls, sa, rr_ls, ortools, nn. SA has no +LS variant (D28);
rr_ls is the random-restart + LS control (D34, ablation only); qpso_cluster is cluster-first
QPSO for large instances (D47).
"+LS" variants use the same LS rule as QPSO (gbest every 10 iterations + memetic LS on the best 25% of new
positions, Lamarckian; D33).
"""
import time

import numpy as np

from qflux.config import load_config


class NearestNeighbour:
    """Fallback / Phase-0 stand-in: NN construction (+ Split re-decode), one evaluation."""
    name = "nn"

    def __init__(self, **params):
        self.p = params

    def run(self, ev, budget_evals=None, budget_s=None, rng=None, callback=None, should_stop=None, init_keys=None):
        from qflux.core.construct import nearest_neighbour_routes
        t = time.time()
        routes = nearest_neighbour_routes(ev.inst)
        perm = np.array([c for r in routes for c in r], dtype=np.int64)
        f = ev.fitness_perm(perm)
        sol = ev.solution(perm)
        sol.meta.update(algo="nn", evals=ev.evals, wall_s=time.time() - t, partial=False)
        return sol, [(ev.evals, f)]


def get_optimizer(name: str, params: dict | None = None):
    params = dict(params or {})
    ls_every = load_config()["qpso"]["ls_every"]
    if name == "qpso":
        from .qpso import QPSO
        return QPSO(**params)
    if name == "qpso_noqubo":                       # D53: default "QuantumRoute engine" (QUBO slot off)
        from .qpso import QPSO
        opt = QPSO(**{"qubo_slot": {"enabled": False}, **params})
        opt.name = "qpso_noqubo"
        return opt
    if name == "qpso_base":
        from .qpso import BASE_QPSO, QPSO
        opt = QPSO(**{**BASE_QPSO, **params})
        opt.name = "qpso_base"
        return opt
    if name in ("pso", "pso_ls"):
        from .pso import PSO
        opt = PSO(**({"ls_every": ls_every} if name == "pso_ls" else {}), **params)
        opt.name = name
        return opt
    if name in ("ga", "ga_ls"):
        from .ga import GA
        opt = GA(**({"ls_every": ls_every} if name == "ga_ls" else {}), **params)
        opt.name = name
        return opt
    if name == "sa":
        from .sa import SA
        return SA(**params)
    if name == "qpso_cluster":
        from .cluster import ClusterQPSO
        return ClusterQPSO(**params)
    if name == "rr_ls":
        from .rrls import RRLS
        return RRLS(**params)
    if name == "ortools":
        from .ortools_wrap import ORTools
        return ORTools(**params)
    if name == "nn":
        return NearestNeighbour(**params)
    raise KeyError(f"unknown optimizer {name!r}")


ALGORITHMS = ("qpso", "qpso_noqubo", "qpso_base", "pso", "pso_ls", "ga", "ga_ls", "sa", "rr_ls", "qpso_cluster", "ortools", "nn")
