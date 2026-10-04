"""Fleet-aware routing: naive vs user equilibrium vs system optimum (§6.6, D5, D6, D22, D23).

Only the dispatch slot is rebuilt each iteration. A dispatch wave is treated as a 1-hour flow: every
route traversal of an edge adds S vehicles/h (S = platform scale factor, a disclosed modelling assumption).
Plans are made with t_e(x) (user_eq) or mc_e(x) (system_opt); every mode is REPORTED with real BPR times
t_e(v0 + S * flow_of(R)) along the paths the plan actually uses.
"""
import time

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from qflux.config import load_config
from qflux.explain.templates import fleet_sentence
from qflux.types import Instance, Refs, Weights

from .bpr import bpr_time
from .emissions import edge_co2_kg
from .profiles import SECONDARY, load_ratio, nearest_slot
from .route_eval import compute_refs, evaluate_routes
from .td_matrix import SlotPaths, TDBundle, all_pairs, bundle_for, edge_times

MODES = ("naive", "user_eq", "system_opt")


def path_sums(paths: SlotPaths, m: int, arr: np.ndarray) -> np.ndarray:
    """(m, m) sums of a per-edge array along every stored path."""
    vals = arr[paths.edges]
    lens = np.diff(paths.ptr)
    starts = paths.ptr[:-1]
    out = np.zeros(m * m)
    nz = lens > 0
    if len(vals):
        out[nz] = np.add.reduceat(vals, starts[nz])
    return out.reshape(m, m)


def flow_of(routes: list[list[int]], paths: SlotPaths, m: int, E: int) -> np.ndarray:
    """Number of route traversals per road edge (one plan, dispatch-slot paths)."""
    f = np.zeros(E)
    for r in routes:
        nodes = [0] + list(r) + [0]
        for a, b in zip(nodes[:-1], nodes[1:]):
            np.add.at(f, paths.get(a, b, m), 1.0)
    return f


class DispatchSlot:
    """Matrices for the dispatch slot under a given planning weight, plus real-time evaluation."""

    def __init__(self, inst: Instance, bundle: TDBundle):
        self.inst, self.b, self.net = inst, bundle, bundle.net
        self.s0 = nearest_slot(inst.tau0, bundle.slot_centers)
        self.t = float(bundle.slot_centers[self.s0])
        self.v0 = load_ratio(self.t, self.net.group) * self.net.capacity
        tr = load_config()["traffic"]
        self.a, self.bb = tr["bpr_a"], tr["bpr_b"]
        from . import events
        self.inc = events.factor_for(self.net, events.slot_incidents(bundle.incidents, bundle.slot_centers)[self.s0])
        self.t_free = edge_times(self.net, self.t, inc_factor=self.inc)       # t_e(v0), no fleet

    def times(self, x: np.ndarray, mode: str = "time") -> np.ndarray:
        return edge_times(self.net, self.t, x=x, mode=mode, inc_factor=self.inc)

    def plan(self, x: np.ndarray | None, mode: str):
        """Paths + planning matrices. mode: 'naive' (x=0, t), 'user_eq' (t(x)), 'system_opt' (mc(x))."""
        if mode == "naive" or x is None:
            return self.b.paths[self.s0], self.b.T_slots[self.s0], self.b.D_slots[self.s0], self.b.E_slots[self.s0]
        w = self.times(x, "mc" if mode == "system_opt" else "time")
        W, _, D, E, _, sp = all_pairs(self.net, self.b.terminals, w, t_real=self.times(x))
        return sp, W, D, E

    def realized(self, routes, paths: SlotPaths, S: float) -> dict:
        m, E = self.b.m, self.net.E
        x = S * flow_of(routes, paths, m, E)
        t_real = self.times(x)
        T = path_sums(paths, m, t_real)
        D = path_sums(paths, m, self.net.length_km)
        CO2 = path_sums(paths, m, edge_co2_kg(self.net.length_km, t_real))
        vc = (self.v0 + x) / self.net.capacity
        used = x > 0
        ext = float((self.v0 * (t_real - self.t_free)).sum() / 60.0)      # veh * min / 60 -> veh-h
        return dict(x=x, T=T, D=D, E=CO2, vc=vc, used=used, externality_veh_h=ext,
                    max_vc=float(vc[used].max()) if used.any() else 0.0,
                    edges_over_capacity=int((vc[used] > 1.0).sum()),
                    corridors_used=corridors(self.net, used))

    def static_bundle(self, T, D, E, paths: SlotPaths) -> TDBundle:
        """A TD bundle whose every slot equals the given dispatch-slot matrices (for reporting)."""
        S = len(self.b.slot_centers)
        rep = lambda M: np.repeat(M[None], S, axis=0)
        return TDBundle(self.net, self.b.terminals, self.b.slot_centers, rep(T), rep(D), rep(E), self.b.T0,
                        rep(T), [paths] * S, self.b.incidents)


def corridors(net, used: np.ndarray) -> int:
    """Distinct corridors = connected groups (undirected) of major-road edges (arterial/secondary)
    carrying fleet flow. Deterministic proxy for 'how many distinct main roads the fleet uses'."""
    sel = used & (net.group <= SECONDARY)
    if not sel.any():
        return 0
    u, v = net.eu[sel], net.ev[sel]
    nodes, inv = np.unique(np.concatenate([u, v]), return_inverse=True)
    k = len(u)
    g = coo_matrix((np.ones(k), (inv[:k], inv[k:])), shape=(len(nodes), len(nodes)))
    return int(connected_components(g, directed=False)[0])


def plan_cost(inst: Instance, w: Weights, refs: Refs, W, D, E, plan_is_time: bool):
    """Weighted §3.4 leg cost for the stand-in / planning matrices (W = planning time or marginal cost)."""
    C = np.maximum(W - inst.T0, 0.0)
    return w.wT * W / refs.T + w.wD * D / refs.D + w.wC * C / refs.C + w.wE * E / refs.E


def run_fleet(inst: Instance, w: Weights, *, modes=MODES, S: float | None = None, iters: int | None = None,
              seed: int = 0, time_s: float = 5.0, solver=None, log=None) -> dict:
    """Returns {mode: {"routes", "paths", "real": realized-metrics, "history": [...], "plan_bundle"}}."""
    tr = load_config()["traffic"]
    S = float(tr["platform_scale_S"] if S is None else S)
    iters = int(tr["fleet_eq_iters"] if iters is None else iters)
    bundle = bundle_for(inst)
    ds = DispatchSlot(inst, bundle)
    refs = compute_refs(inst, bundle)
    solver = solver or _default_solver(inst, w, refs, time_s, seed)
    out: dict = {}

    t = time.time()
    paths0, W0, D0, E0 = ds.plan(None, "naive")
    R0 = solver(W0, D0, E0, None)
    naive = dict(routes=R0, paths=paths0, history=[], real=ds.realized(R0, paths0, S), wall_s=time.time() - t)
    out["naive"] = naive
    for mode in [m for m in modes if m != "naive"]:
        t = time.time()
        x = np.zeros(bundle.net.E)
        R, paths = R0, paths0
        hist = []
        for k in range(1, iters + 1):
            y = S * flow_of(R, paths, bundle.m, bundle.net.E)
            x_new = x + (y - x) / k                                   # MSA
            hist.append(dict(k=k, step_norm=float(np.linalg.norm(x_new - x))))
            x = x_new
            paths, W, D, E = ds.plan(x, mode)
            R = solver(W, D, E, R)
            if log:
                log(f"{mode} k={k} |dx|={hist[-1]['step_norm']:.1f}")
        out[mode] = dict(routes=R, paths=paths, history=hist, real=ds.realized(R, paths, S), wall_s=time.time() - t)
    out["_ds"], out["_refs"], out["_S"] = ds, refs, S
    return out


def _default_solver(inst, w, refs, time_s, seed):
    """solve(W, D, E, warm_routes) -> routes on the dispatch-slot planning matrices.

    With Person A's engine: QPSO on a one-slot planning instance (full budget cold, 50 iterations when
    warm-started, §6.6.2). Otherwise the OR-Tools stand-in on the same weighted matrix."""
    from qflux.dynamic.solver import engine_available, solve
    if engine_available():
        cfg = load_config()
        N = int(cfg["qpso"]["N"])

        def solve_engine(W, D, E, warm):
            plan = Instance(name=f"{inst.name}#plan", source=inst.source, n=inst.n, Q=inst.Q, K=inst.K,
                            demand=inst.demand, service=inst.service, coords=inst.coords, D=D,
                            slot_centers=np.array([inst.tau0]), T_slots=W[None], T0=inst.T0,
                            D_slots=D[None], E_slots=E[None], tau0=inst.tau0)
            perm = None if warm is None else [c for r in warm for c in r]
            evals = cfg["budget"]["evals"] if warm is None else 50 * N
            from qflux.algos.registry import DEFAULT_ENGINE
            return solve(plan, w, refs, algorithm=DEFAULT_ENGINE, seed=seed, budget={"evals": evals},
                         warm_start_perm=perm)["routes"]
        return solve_engine

    from qflux.dynamic.standin import solve_ortools

    def solve_standin(W, D, E, warm):
        return solve_ortools(inst, w, refs, time_limit_s=time_s, cost_matrix=plan_cost(inst, w, refs, W, D, E, True),
                             warm_start_routes=warm)["routes"]
    return solve_standin


def fleet_result(inst: Instance, w: Weights, res: dict, mode: str, *, seed: int, scenario_id: str) -> dict:
    """FleetResult = ResultJSON + {externality_veh_h, max_vc, edges_over_capacity, corridors_used}."""
    from .result_json import build_result
    ds, refs, S = res["_ds"], res["_refs"], res["_S"]
    r = res[mode]
    real = r["real"]
    rb = ds.static_bundle(real["T"], real["D"], real["E"], r["paths"])
    ev = evaluate_routes(inst, rb, r["routes"], w, refs)
    note = [f"Fleet mode {mode}: planned with {'marginal cost' if mode == 'system_opt' else 'current travel times'}"
            f", reported with real BPR times at the dispatch slot; S = {S:g} vehicle-equivalents per route "
            f"(modelling assumption)."]
    from qflux.dynamic.solver import engine_available
    algo = "qpso" if engine_available() else "ortools-standin"
    out = build_result(inst, rb, r["routes"], w, refs, algorithm=algo, seed=seed,
                       runtime_s=r["wall_s"], evals=0, convergence=[], job_id=f"fleet-{mode}",
                       scenario_id=scenario_id, ev=ev, extra_explanation=note)
    net, used = ds.net, real["used"]
    idx = np.flatnonzero(used)
    out["edge_flows"] = [dict(geometry=[net.node_xy[net.eu[e]].round(6).tolist(), net.node_xy[net.ev[e]].round(6).tolist()],
                              fleet_flow=round(float(real["x"][e]), 2), vc_ratio=round(float(real["vc"][e]), 3))
                         for e in idx]
    out.update(externality_veh_h=round(real["externality_veh_h"], 3), max_vc=round(real["max_vc"], 3),
               edges_over_capacity=real["edges_over_capacity"], corridors_used=real["corridors_used"])
    return out


def fleet_compare_request(inst: Instance, req: dict, scenario_id: str = "") -> dict:
    from qflux.api import weights_from
    w = weights_from(req.get("weights"))
    modes = tuple(req.get("modes") or MODES)
    res = run_fleet(inst, w, modes=modes, S=req.get("S"), seed=int(req.get("seed", 0)),
                    time_s=float(req.get("time_s", 5.0)))
    out = {m: fleet_result(inst, w, res, m, seed=int(req.get("seed", 0)), scenario_id=scenario_id)
           for m in modes if m in res}
    if "naive" in out and "system_opt" in out:
        out["system_opt"]["explanation"].insert(0, fleet_sentence(out["naive"], out["system_opt"]))
    return {"modes": out, "S": res["_S"], "msa_history": {m: res[m]["history"] for m in out}}
