"""Backends for the quantum-ready sub-route slot (§7.7.3): solve_route_order(route, dist, backend).

neal = classical simulated annealing (dwave-samplers) on the QUBO. The "one-line swap" claim is
backend="dwave", which needs a Leap token and is a stub here. No quantum hardware is used today.
"""
import itertools
import time

import numpy as np

from .qubo_route import build_route_qubo, decode, qubo_matrix, tour_cost

MAX_STOPS = 7


def _brute(route, dist):
    best = min(itertools.permutations(route), key=lambda p: tour_cost(p, dist))
    return list(best)


def _heldkarp(route, dist):
    from qflux.algos.heldkarp import held_karp_tour
    return held_karp_tour(route, dist)


def _two_opt(route, dist):
    seq = [0] + list(route) + [0]
    improved = True
    while improved:
        improved = False
        for i in range(1, len(seq) - 2):
            for j in range(i + 1, len(seq) - 1):
                if dist[seq[i - 1], seq[j]] + dist[seq[i], seq[j + 1]] < dist[seq[i - 1], seq[i]] + dist[seq[j], seq[j + 1]] - 1e-12:
                    seq[i:j + 1] = seq[i:j + 1][::-1]
                    improved = True
    return seq[1:-1]


def _neal(route, dist, num_reads=200, A=None, seed=None):
    from dwave.samplers import SimulatedAnnealingSampler
    Q = build_route_qubo(route, dist, A)
    ss = SimulatedAnnealingSampler().sample_qubo(Q, num_reads=num_reads, seed=seed)
    for rec in ss.data(["sample", "energy"], sorted_by="energy"):
        order = decode(dict(rec.sample), route)
        if order is not None:
            return order, float(rec.energy)
    return None, float(ss.first.energy)


def solve_route_order(route, dist, backend: str = "neal", **kw) -> dict:
    """{order, energy, feasible, time_s}. Infeasible sample -> original route with feasible=False (T31)."""
    route = list(route)
    t = time.time()
    energy = None
    if backend == "neal":
        order, energy = _neal(route, dist, kw.get("num_reads", 200), kw.get("A"), kw.get("seed"))
    elif backend == "brute":
        if len(route) > 8:
            raise ValueError("brute force limited to 8 stops")
        order = _brute(route, dist)
    elif backend == "heldkarp":
        order = _heldkarp(route, dist)
    elif backend == "2opt":
        order = _two_opt(route, dist)
    elif backend == "qiskit":
        raise NotImplementedError("qiskit QAOA backend is optional (cut list #2)")
    elif backend == "dwave":
        raise NotImplementedError("D-Wave Leap backend stub: set DWAVE_API_TOKEN and implement the sampler call")
    else:
        raise ValueError(f"unknown backend {backend}")
    feasible = order is not None
    if not feasible:
        order = route
    return {"order": [int(c) for c in order], "energy": energy, "feasible": feasible,
            "time_s": time.time() - t, "cost": tour_cost(order, dist)}


def solve_route_request(req: dict) -> dict:
    """POST /quantum/solve-route: {route_stops, backend, dist?} -> {order, energy, feasible, qubo_matrix, time_s, optimal_cost}."""
    stops = [int(s) for s in req["route_stops"]]
    if len(stops) > MAX_STOPS:
        raise ValueError(f"at most {MAX_STOPS} stops")
    if "dist" in req:
        dist = np.asarray(req["dist"], float)
        local = stops
    else:  # coordinates-free demo: stops index into a provided/unit matrix
        raise ValueError("dist matrix required")
    out = solve_route_order(local, dist, req.get("backend", "neal"), seed=req.get("seed"))
    Q = build_route_qubo(local, dist)
    out["qubo_matrix"] = qubo_matrix(Q, len(local) ** 2).round(4).tolist()
    out["optimal_cost"] = tour_cost(_brute(local, dist), dist)
    return out
