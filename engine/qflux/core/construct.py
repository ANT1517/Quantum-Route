"""Nearest-neighbour construction (§7.2) and the fixed references it provides (§3.4)."""
import numpy as np

from qflux.types import Instance, Refs


def dispatch_matrix(inst: Instance) -> np.ndarray:
    """Travel-time matrix at the slot nearest tau0 (static instances: D)."""
    if inst.T_slots is None:
        return inst.D
    c = np.asarray(inst.slot_centers, float)
    d = np.abs(((c - inst.tau0 % 1440.0) + 720.0) % 1440.0 - 720.0)
    return inst.T_slots[int(np.argmin(d))]


def nearest_neighbour_routes(inst: Instance) -> list[list[int]]:
    """Go to the nearest unserved customer that fits the remaining capacity, else return to the depot."""
    T = dispatch_matrix(inst)
    left = set(range(1, inst.n + 1))
    routes = []
    while left:
        cur, load, r = 0, 0.0, []
        while True:
            cand = [c for c in left if load + inst.demand[c] <= inst.Q]
            if not cand:
                break
            nxt = min(cand, key=lambda c: (T[cur, c], c))
            r.append(nxt); load += inst.demand[nxt]; left.discard(nxt); cur = nxt
        if not r:
            raise ValueError("a customer demand exceeds Q")
        routes.append(r)
    return routes


def reference_values(inst: Instance, ev) -> Refs:
    """References from the NN solution, computed once per instance and never changed (D3).
    C_ref = max(C_nn, 0.05 * T_nn) so the congestion term never divides by ~0 at night."""
    T, D, C, E = ev.components(nearest_neighbour_routes(inst))
    return Refs(T=T, D=D, C=max(C, 0.05 * T), E=E)
