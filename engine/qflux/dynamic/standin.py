"""OR-Tools stand-in solver (Person B's folder) so fleet, incident and demo work runs before the QPSO merge.

It plans on a static weighted matrix at the dispatch slot (§3.4 weights, fixed references), then routes are
re-evaluated time-dependently by `route_eval`. Results are always labelled algorithm="ortools".
"""
import time

import numpy as np

from qflux.traffic.profiles import nearest_slot
from qflux.types import Instance, Refs, Weights

SCALE = 1_000_000


def weighted_matrix(inst: Instance, w: Weights, refs: Refs, T: np.ndarray | None = None) -> np.ndarray:
    """Dispatch-slot leg cost following the §3.4 weights. `T` overrides the planning time matrix
    (the fleet loop passes BPR or marginal-cost times)."""
    s = nearest_slot(inst.tau0, inst.slot_centers)
    T = inst.T_slots[s] if T is None else T
    C = np.maximum(T - inst.T0, 0.0)
    return (w.wT * T / refs.T + w.wD * inst.D_slots[s] / refs.D + w.wC * C / refs.C
            + w.wE * inst.E_slots[s] / refs.E)


def solve_ortools(inst: Instance, w: Weights, refs: Refs, *, time_limit_s: float = 5.0, cost_matrix=None,
                  warm_start_routes=None, progress=None, requested: str = "ortools") -> dict:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    cost = weighted_matrix(inst, w, refs) if cost_matrix is None else cost_matrix
    icost = np.rint(cost * SCALE).astype(np.int64)
    n = inst.n
    K = inst.K if inst.K is not None else n
    demand = np.rint(inst.demand).astype(int).tolist()
    t_start = time.time()

    for vehicles in (K, K + 2, K + 5):
        mgr = pywrapcp.RoutingIndexManager(n + 1, vehicles, 0)
        routing = pywrapcp.RoutingModel(mgr)
        cb = routing.RegisterTransitCallback(
            lambda a, b: int(icost[mgr.IndexToNode(a), mgr.IndexToNode(b)]))
        routing.SetArcCostEvaluatorOfAllVehicles(cb)
        dcb = routing.RegisterUnaryTransitCallback(lambda a: demand[mgr.IndexToNode(a)])
        routing.AddDimensionWithVehicleCapacity(dcb, 0, [int(inst.Q)] * vehicles, True, "load")
        if vehicles > K:        # extra vehicles only when K is too tight; penalise like λ (§3.4)
            for v in range(K, vehicles):
                routing.SetFixedCostOfVehicle(int(w.lam * SCALE), v)
        params = pywrapcp.DefaultRoutingSearchParameters()
        params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        params.time_limit.FromMilliseconds(int(time_limit_s * 1000))

        curve: list[dict] = []

        def on_solution():
            k = len(curve)
            curve.append(dict(iter=k, evals=k + 1, best_F=routing.CostVar().Max() / SCALE))
            if progress and k % 5 == 0:
                progress(dict(iter=k, evals=k + 1, best_F=curve[-1]["best_F"],
                              elapsed_s=time.time() - t_start))

        routing.AddAtSolutionCallback(on_solution)
        sol = None
        if warm_start_routes:
            routing.CloseModelWithParameters(params)
            init = routing.ReadAssignmentFromRoutes([list(r) for r in warm_start_routes][:vehicles], True)
            if init is not None:
                sol = routing.SolveFromAssignmentWithParameters(init, params)
        if sol is None:
            sol = routing.SolveWithParameters(params)
        if sol is not None:
            routes = []
            for v in range(vehicles):
                idx, r = routing.Start(v), []
                while not routing.IsEnd(idx):
                    node = mgr.IndexToNode(idx)
                    if node:
                        r.append(int(node))
                    idx = sol.Value(routing.NextVar(idx))
                if r:
                    routes.append(r)
            best = [dict(c, best_F=min(x["best_F"] for x in curve[: i + 1])) for i, c in enumerate(curve)]
            return dict(routes=routes, algorithm="ortools", requested=requested, evals=len(curve),
                        convergence=best, partial=False, perm=[c for r in routes for c in r],
                        wall_s=time.time() - t_start)
    raise RuntimeError("OR-Tools stand-in found no feasible solution")
