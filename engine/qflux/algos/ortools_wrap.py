"""OR-Tools industry reference (§7.8): PATH_CHEAPEST_ARC + GUIDED_LOCAL_SEARCH on the static (dispatch-slot)
weighted matrix, capacity dimension, integer costs. Time budget only; we do not claim to beat it."""
import time

import numpy as np

from qflux.config import load_config

SCALE = 1000


class ORTools:
    name = "ortools"

    def __init__(self, **params):
        self.p = {**load_config()["ortools"], **params}

    def run(self, ev, budget_evals=None, budget_s=None, rng=None, callback=None, should_stop=None, init_keys=None):
        t0 = time.time()                    # the budget includes imports and model building (D31)
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2

        from qflux.algos.qpso import dispatch_cost_matrix
        inst = ev.inst
        C = dispatch_cost_matrix(ev)
        if inst.source == "cvrplib" and ev.wv[1] == 1.0 and not ev.wv[[0, 2, 3]].any():
            icost = np.rint(inst.D).astype(np.int64)             # integer CVRPLIB distances (nint)
            if inst.distance_convention == "exact":
                icost = np.rint(inst.D * SCALE).astype(np.int64)
        else:
            icost = np.rint(C * 1e6).astype(np.int64)
        n = inst.n
        V = inst.K if inst.K is not None else n
        mgr = pywrapcp.RoutingIndexManager(n + 1, V, 0)
        routing = pywrapcp.RoutingModel(mgr)
        cb = routing.RegisterTransitCallback(lambda a, b: int(icost[mgr.IndexToNode(a), mgr.IndexToNode(b)]))
        routing.SetArcCostEvaluatorOfAllVehicles(cb)
        dem = np.rint(inst.demand).astype(int).tolist()
        dcb = routing.RegisterUnaryTransitCallback(lambda a: dem[mgr.IndexToNode(a)])
        routing.AddDimensionWithVehicleCapacity(dcb, 0, [int(inst.Q)] * V, True, "load")
        prm = pywrapcp.DefaultRoutingSearchParameters()
        prm.first_solution_strategy = getattr(routing_enums_pb2.FirstSolutionStrategy, self.p["first_solution"])
        prm.local_search_metaheuristic = getattr(routing_enums_pb2.LocalSearchMetaheuristic, self.p["metaheuristic"])
        limit = float(budget_s if budget_s is not None else self.p["time_limit_s"])
        # D31: the solver gets what is left of the budget after model building, minus a small margin
        # for extracting and evaluating the routes
        remaining = limit - (time.time() - t0) - min(0.1, 0.005 * limit)
        prm.time_limit.FromMilliseconds(max(100, int(remaining * 1000)))
        curve: list = []
        found: list = []

        def on_sol():
            found.append(routing.CostVar().Max())
            if callback is not None and len(found) % 5 == 1:
                callback({"iter": len(found), "evals": len(found), "best_F": float(min(found)),
                          "elapsed_s": time.time() - t0})
        routing.AddAtSolutionCallback(on_sol)
        sol = routing.SolveWithParameters(prm)
        if sol is None:
            raise RuntimeError("OR-Tools found no solution")
        routes = []
        for v in range(V):
            idx, r = routing.Start(v), []
            while not routing.IsEnd(idx):
                node = mgr.IndexToNode(idx)
                if node:
                    r.append(int(node))
                idx = sol.Value(routing.NextVar(idx))
            if r:
                routes.append(r)
        out = ev.solution_from_routes(routes)
        out.meta.update(algo=self.name, evals=0, solutions_found=len(found), wall_s=time.time() - t0, partial=False)
        return out, [(0, out.F)]
