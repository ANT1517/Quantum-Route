"""Evaluate routes on a TD bundle following the §3.3 clock, and build the per-route part of ResultJSON.

This is Person B's evaluator for the traffic/fleet/demo code paths. Person A's core Evaluator (Split,
fitness) is the one used inside optimizers; both follow the same §3.3/§3.4 definitions.
"""
import numpy as np

from qflux.types import Instance, Refs, Weights

from .profiles import nearest_slot, slot_weights
from .td_matrix import TDBundle

PALETTE = ["#14b8a6", "#f59e0b", "#8b5cf6", "#ef4444", "#3b82f6", "#22c55e", "#ec4899", "#0ea5e9",
           "#a16207", "#6366f1", "#84cc16", "#f97316"]


def route_legs(inst: Instance, bundle: TDBundle, route: list[int], tau0: float | None = None):
    """Yield per-leg dicts {i, j, depart, T, D, C, E} for depot -> route -> depot."""
    t = inst.tau0 if tau0 is None else tau0
    nodes = [0] + list(route) + [0]
    legs = []
    for a, b in zip(nodes[:-1], nodes[1:]):
        t_dep = t + inst.service[a]
        T, D, C, E = bundle.leg(a, b, t_dep)
        legs.append(dict(i=a, j=b, depart=t_dep, T=T, D=D, C=C, E=E))
        t = t_dep + T
    return legs


def evaluate_routes(inst: Instance, bundle: TDBundle, routes: list[list[int]], w: Weights | None = None,
                    refs: Refs | None = None, tau0: float | None = None) -> dict:
    """Totals and per-route metrics. F follows §3.4 when weights and refs are given."""
    per, tot = [], dict(T=0.0, D=0.0, C=0.0, E=0.0)
    for r in routes:
        if not r:
            continue
        legs = route_legs(inst, bundle, r, tau0)
        m = {k: float(sum(l[k] for l in legs)) for k in ("T", "D", "C", "E")}
        m.update(legs=legs, load=float(inst.demand[r].sum()), depart=legs[0]["depart"],
                 ret=legs[-1]["depart"] + legs[-1]["T"])
        per.append(m)
        for k in tot:
            tot[k] += m[k]
    out = dict(routes=per, n_vehicles=len(per), **tot)
    if w is not None and refs is not None:
        out["F"] = fitness(tot, len(per), inst.K, w, refs)
    return out


def fitness(tot: dict, m: int, K: int | None, w: Weights, refs: Refs) -> float:
    F = (w.wT * tot["T"] / refs.T + w.wD * tot["D"] / refs.D + w.wC * tot["C"] / refs.C
         + w.wE * tot["E"] / refs.E)
    if K is not None:
        F += w.lam * max(0, m - K)
    return float(F)


def nearest_neighbour_routes(inst: Instance, bundle: TDBundle) -> list[list[int]]:
    """§7.2 NN construction on the dispatch-slot times (used for fixed references)."""
    s = nearest_slot(inst.tau0, bundle.slot_centers)
    T = bundle.T_slots[s]
    left = set(range(1, inst.n + 1))
    routes = []
    while left:
        cur, load, r = 0, 0.0, []
        while True:
            cand = [c for c in left if load + inst.demand[c] <= inst.Q]
            if not cand:
                break
            nxt = min(cand, key=lambda c: T[cur, c])
            r.append(nxt); load += inst.demand[nxt]; left.discard(nxt); cur = nxt
        routes.append(r)
    return routes


def compute_refs(inst: Instance, bundle: TDBundle) -> Refs:
    ev = evaluate_routes(inst, bundle, nearest_neighbour_routes(inst, bundle))
    return Refs(T=ev["T"], D=ev["D"], C=max(ev["C"], 0.05 * ev["T"]), E=ev["E"])


def routes_json(inst: Instance, bundle: TDBundle, ev: dict, routes: list[list[int]]) -> list[dict]:
    """The `routes` array of ResultJSON with road geometry (slot nearest to each leg's departure)."""
    out = []
    kept = [r for r in routes if r]
    for v, (r, m) in enumerate(zip(kept, ev["routes"])):
        geom: list[list[float]] = []
        for leg in m["legs"]:
            s, s1, lam = slot_weights(leg["depart"], bundle.slot_centers)
            g = bundle.path_geometry(s if lam < 0.5 else s1, leg["i"], leg["j"])
            geom.extend(g if not geom else g[1:])
        out.append(dict(vehicle=v + 1, stops=[int(c) for c in r], load=m["load"], capacity=float(inst.Q),
                        time_min=round(m["T"], 3), distance_km=round(m["D"], 3),
                        congestion_delay_min=round(m["C"], 3), co2_kg=round(m["E"], 4),
                        depart_min=round(m["depart"], 2), return_min=round(m["ret"], 2),
                        geometry=geom, color=PALETTE[v % len(PALETTE)]))
    return out


def giant_tour(routes: list[list[int]]) -> np.ndarray:
    return np.array([c for r in routes for c in r], dtype=np.int64)
