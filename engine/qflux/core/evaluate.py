"""Evaluator (§5.2, §3.4): Split decode, component breakdown, fixed references, evaluation counter."""
import numpy as np

from qflux.types import Instance, Refs, Solution, Weights

from .split import count_routes, extract_routes, route_components, route_cost_arr, split_td


def pack_arrays(inst: Instance):
    """(centers, Ts, Ds, Es, T0) as contiguous float64 arrays; static instances become one slot."""
    if inst.T_slots is not None:
        centers = np.ascontiguousarray(inst.slot_centers, dtype=np.float64)
        Ts = np.ascontiguousarray(inst.T_slots, dtype=np.float64)
        Ds = np.ascontiguousarray(inst.D_slots, dtype=np.float64)
        Es = np.ascontiguousarray(inst.E_slots if inst.E_slots is not None else np.zeros_like(inst.T_slots))
        T0 = np.ascontiguousarray(inst.T0 if inst.T0 is not None else inst.T_slots.min(axis=0), dtype=np.float64)
    else:
        D = np.ascontiguousarray(inst.D, dtype=np.float64)
        centers = np.zeros(1)
        Ts = D[None].copy()
        Ds = D[None].copy()
        Es = np.zeros_like(Ts)
        T0 = D.copy()
    return centers, Ts, Ds, Es, T0


class Evaluator:
    def __init__(self, inst: Instance, w: Weights, refs: Refs | None = None):
        self.inst, self.w = inst, w
        self.centers, self.Ts, self.Ds, self.Es, self.T0 = pack_arrays(inst)
        self.service = np.ascontiguousarray(inst.service, dtype=np.float64)
        self.demand = np.ascontiguousarray(inst.demand, dtype=np.float64)
        self.Q = float(inst.Q)
        self.tau0 = float(inst.tau0)
        self.wv = np.array([w.wT, w.wD, w.wC, w.wE], dtype=np.float64)
        self.rv = np.ones(4)                      # placeholder until references are known
        if refs is None:
            from .construct import reference_values
            refs = reference_values(inst, self)
        self.refs = refs
        self.rv = np.array([max(refs.T, 1e-9), max(refs.D, 1e-9), max(refs.C, 1e-9), max(refs.E, 1e-9)])
        self.evals = 0

    # ---- kernels -------------------------------------------------------------------------------
    def _split(self, perm):
        return split_td(np.ascontiguousarray(perm, dtype=np.int64), self.demand, self.Q, self.centers,
                        self.Ts, self.Ds, self.Es, self.T0, self.service, self.tau0, self.wv, self.rv)

    def penalty(self, m: int) -> float:
        K = self.inst.K
        return self.w.lam * max(0, m - K) if K is not None else 0.0

    # ---- public API (§5.2) -------------------------------------------------------------------
    def fitness_perm(self, perm) -> float:
        """One full evaluation (counted)."""
        self.evals += 1
        cost, pred = self._split(perm)
        return float(cost) + self.penalty(count_routes(pred, len(perm)))

    def route_cost(self, route) -> float:
        """Weighted cost of one route (for LS / QUBO; not counted)."""
        seq = np.ascontiguousarray(route, dtype=np.int64)
        return float(route_cost_arr(seq, len(seq), self.centers, self.Ts, self.Ds, self.Es, self.T0,
                                    self.service, self.tau0, self.wv, self.rv))

    def components(self, routes) -> tuple[float, float, float, float]:
        tot = np.zeros(4)
        for r in routes:
            if r:
                seq = np.ascontiguousarray(r, dtype=np.int64)
                tot += route_components(seq, len(seq), self.centers, self.Ts, self.Ds, self.Es, self.T0,
                                        self.service, self.tau0, self.wv, self.rv)
        return tuple(float(x) for x in tot)

    def routes_F(self, routes) -> float:
        return sum(self.route_cost(r) for r in routes if r) + self.penalty(sum(1 for r in routes if r))

    def solution_from_routes(self, routes, meta: dict | None = None) -> Solution:
        routes = [list(map(int, r)) for r in routes if r]
        T, D, C, E = self.components(routes)
        from .feasibility import quick_feasible
        return Solution(perm=np.array([c for r in routes for c in r], dtype=np.int64), routes=routes,
                        F=self.routes_F(routes), T=T, D=D, C=C, E=E, n_vehicles=len(routes),
                        feasible=quick_feasible(self.inst, routes), meta=dict(meta or {}))

    def solution(self, perm) -> Solution:
        """Decode a giant tour (not counted; call fitness_perm for counted evaluations)."""
        perm = np.asarray(perm, dtype=np.int64)
        _, pred = self._split(perm)
        return self.solution_from_routes(extract_routes(perm, pred))

    def decode_routes(self, perm) -> list[list[int]]:
        perm = np.asarray(perm, dtype=np.int64)
        _, pred = self._split(perm)
        return extract_routes(perm, pred)
