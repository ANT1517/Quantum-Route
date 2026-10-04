"""OR-Tools diagnostic (D54 check): is the configuration doing what we think? Bugs only, no tuning.

    python scripts/diag_ortools.py [--instance CMT1] [--time-s 120]

Reports vehicles given, cost scaling, capacity, time limit used vs requested, solver status, number of
solutions found and when the last improvement happened, and our recomputed distance/gap. Also runs the same
model with the costs registered as a C++-side matrix (RegisterTransitMatrix) instead of a Python callback, to
see whether callback overhead limits the search.
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

import numpy as np  # noqa: E402

from qflux.bench.loader import load_instance  # noqa: E402
from qflux.core.evaluate import Evaluator  # noqa: E402
from qflux.core.feasibility import check  # noqa: E402
from qflux.types import Weights  # noqa: E402

SCALE = 1000


def solve(inst, time_s, matrix_api: bool):
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    icost = np.rint(inst.D * (SCALE if inst.distance_convention == "exact" else 1)).astype(np.int64)
    n = inst.n
    V = inst.K if inst.K is not None else n
    mgr = pywrapcp.RoutingIndexManager(n + 1, V, 0)
    routing = pywrapcp.RoutingModel(mgr)
    if matrix_api:
        cb = routing.RegisterTransitMatrix(icost.tolist())
    else:
        cb = routing.RegisterTransitCallback(lambda a, b: int(icost[mgr.IndexToNode(a), mgr.IndexToNode(b)]))
    routing.SetArcCostEvaluatorOfAllVehicles(cb)
    dem = np.rint(inst.demand).astype(int).tolist()
    dcb = routing.RegisterUnaryTransitCallback(lambda a: dem[mgr.IndexToNode(a)])
    routing.AddDimensionWithVehicleCapacity(dcb, 0, [int(inst.Q)] * V, True, "load")
    prm = pywrapcp.DefaultRoutingSearchParameters()
    prm.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    prm.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    prm.time_limit.FromMilliseconds(int(time_s * 1000))
    found, t0 = [], time.time()
    routing.AddAtSolutionCallback(lambda: found.append((time.time() - t0, routing.CostVar().Max())))
    sol = routing.SolveWithParameters(prm)
    wall = time.time() - t0
    routes = []
    for v in range(V):
        idx, r = routing.Start(v), []
        while not routing.IsEnd(idx):
            if mgr.IndexToNode(idx):
                r.append(mgr.IndexToNode(idx))
            idx = sol.Value(routing.NextVar(idx))
        if r:
            routes.append(r)
    best_t = min(found, key=lambda x: x[1])[0] if found else None
    return {"status": routing.status(), "wall_s": wall, "solutions": len(found), "last_improvement_s": best_t,
            "routes": routes, "vehicles_given": V, "scale": SCALE if inst.distance_convention == "exact" else 1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", default="CMT1")
    ap.add_argument("--time-s", type=float, nargs="+", default=[30, 120])
    a = ap.parse_args()
    inst = load_instance(a.instance)
    ev = Evaluator(inst, Weights(wT=0, wD=1))
    print(f"{a.instance}: n={inst.n} Q={inst.Q:g} K={inst.K} convention={inst.distance_convention} BKS={inst.bks}")
    for matrix_api in (False, True):
        for ts in a.time_s:
            r = solve(inst, ts, matrix_api)
            s = ev.solution_from_routes(r["routes"])
            ok = check(inst, s, ev)[0]
            print(f"  {'matrix  ' if matrix_api else 'callback'} limit {ts:>5g}s: wall {r['wall_s']:6.1f}s status {r['status']} "
                  f"solutions {r['solutions']:5d} last improvement at {r['last_improvement_s']:.1f}s | vehicles given "
                  f"{r['vehicles_given']}, used {len(r['routes'])}, scale {r['scale']} | D {s.D:.2f} gap "
                  f"{100 * (s.D - inst.bks) / inst.bks:.2f}% feasible {ok}")


if __name__ == "__main__":
    main()
