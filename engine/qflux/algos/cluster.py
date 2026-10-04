"""Cluster-first QPSO for large instances (§7.13, D47).

1. Sweep clustering: customers sorted by polar angle around the depot, cut into ceil(n / target) clusters of
   near-equal size (target 125 customers, §7.13's 100-150).
2. One QPSO-full per cluster on a sub-instance (same depot, same distance convention), with a share of the
   time budget proportional to the cluster size. Clusters run one after another in this process, so a run
   still uses one core (D30); §7.13's parallel execution would give the clustered run more CPU than the
   direct runs it is compared with.
3. Concatenate the routes, then inter-cluster repair: relocate + swap LS over all routes (boundary customers
   can move to a neighbouring cluster's route), within the remaining time.
Evaluations of the sub-runs are added to the caller's counter. Honest note (§7.13): this shows scalability
behaviour, not state-of-the-art quality on X instances.
"""
import math
import time

import numpy as np

from qflux.core.evaluate import Evaluator
from qflux.core.localsearch import improve_routes
from qflux.types import Instance, Weights

from .curve import TimeCurve


def sweep_clusters(inst: Instance, target: int = 125) -> list[np.ndarray]:
    xy = inst.coords[1:] - inst.coords[0]
    ang = np.arctan2(xy[:, 1], xy[:, 0])
    order = np.argsort(ang, kind="stable") + 1
    k = max(1, math.ceil(inst.n / target))
    return [np.asarray(c, dtype=np.int64) for c in np.array_split(order, k)]


def sub_instance(inst: Instance, members: np.ndarray) -> Instance:
    idx = np.concatenate([[0], members])
    return Instance(name=f"{inst.name}-c{len(members)}", source=inst.source, n=len(members), Q=inst.Q, K=None,
                    demand=inst.demand[idx], service=inst.service[idx],
                    coords=None if inst.coords is None else inst.coords[idx],
                    distance_convention=inst.distance_convention,
                    D=None if inst.D is None else inst.D[np.ix_(idx, idx)], tau0=inst.tau0)


class ClusterQPSO:
    name = "qpso_cluster"

    def __init__(self, target: int = 125, repair_frac: float = 0.10, **qpso_params):
        self.target, self.repair_frac, self.qpso_params = int(target), float(repair_frac), qpso_params

    def run(self, ev, budget_evals=None, budget_s=None, rng=None, callback=None, should_stop=None, init_keys=None):
        from .qpso import QPSO
        inst = ev.inst
        if inst.T_slots is not None:
            raise ValueError("qpso_cluster is for static instances (CVRPLIB)")
        t0 = time.time()
        deadline = t0 + budget_s if budget_s is not None else None
        clusters = sweep_clusters(inst, self.target)
        w = Weights(*[float(x) for x in ev.wv], lam=ev.w.lam)
        routes, sub_evals, meta_clusters = [], 0, []
        ct = TimeCurve(t0)
        solve_s = None if budget_s is None else budget_s * (1.0 - self.repair_frac)
        for members in clusters:
            share = len(members) / inst.n
            sub = sub_instance(inst, members)
            sev = Evaluator(sub, w)
            b_s = None if solve_s is None else max(0.1, share * solve_s)
            if deadline is not None:
                b_s = max(0.05, min(b_s, deadline - time.time()))
            b_e = None if budget_evals is None else max(1, int(share * budget_evals))
            sol, _ = QPSO(**self.qpso_params).run(sev, b_e, b_s, rng)
            routes += [[int(members[c - 1]) for c in r] for r in sol.routes]   # local ids -> global ids
            sub_evals += sev.evals
            meta_clusters.append({"size": int(len(members)), "routes": len(sol.routes), "evals": sev.evals})
        ev.evals += sub_evals
        ct.add(ev.routes_F(routes))
        repaired = improve_routes(routes, ev, ("relocate", "swap", "2opt"), deadline=deadline)
        if ev.routes_F(repaired) <= ev.routes_F(routes):
            routes = repaired
        out = ev.solution_from_routes(routes)
        out.meta.update(algo=self.name, evals=ev.evals, wall_s=time.time() - t0, partial=False,
                        clusters=meta_clusters, ls_calls=1, curve_t=ct.final(out.F))
        return out, [(ev.evals, out.F)]
