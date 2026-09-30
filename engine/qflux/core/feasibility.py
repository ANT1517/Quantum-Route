"""Independent feasibility checker (§3.5): recomputes coverage, loads and costs from the routes alone."""
import numpy as np

from qflux.types import Instance, Solution


def quick_feasible(inst: Instance, routes) -> bool:
    seen = [c for r in routes for c in r]
    if sorted(seen) != list(range(1, inst.n + 1)):
        return False
    return all(float(np.sum(inst.demand[list(r)])) <= inst.Q + 1e-9 for r in routes if r)


def check(inst: Instance, sol: Solution, ev=None, tol: float = 1e-6) -> tuple[bool, list[str]]:
    errs: list[str] = []
    seen: dict[int, int] = {}
    for k, r in enumerate(sol.routes):
        for c in r:
            if not 1 <= c <= inst.n:
                errs.append(f"route {k}: invalid customer {c}")
            seen[c] = seen.get(c, 0) + 1
        load = float(np.sum(inst.demand[list(r)])) if r else 0.0
        if load > inst.Q + 1e-9:
            errs.append(f"route {k}: load {load:g} > Q {inst.Q:g}")
    for c, cnt in seen.items():
        if cnt > 1:
            errs.append(f"customer {c} served {cnt} times")
    missing = set(range(1, inst.n + 1)) - set(seen)
    if missing:
        errs.append(f"customers not served: {sorted(missing)[:10]}")
    if sol.n_vehicles != sum(1 for r in sol.routes if r):
        errs.append("n_vehicles does not match routes")
    if ev is not None and not errs:
        T, D, C, E = ev.components(sol.routes)
        for name, a, b in (("T", T, sol.T), ("D", D, sol.D), ("C", C, sol.C), ("E", E, sol.E)):
            if abs(a - b) > tol * max(1.0, abs(a)):
                errs.append(f"component {name} mismatch: recomputed {a:.6g} vs reported {b:.6g}")
        F = ev.routes_F(sol.routes)
        if abs(F - sol.F) > tol * max(1.0, abs(F)):
            errs.append(f"F mismatch: recomputed {F:.6g} vs reported {sol.F:.6g}")
    return (not errs), errs
