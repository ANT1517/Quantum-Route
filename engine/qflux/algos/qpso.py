"""Quantum-behaved PSO for TD-CVRP (§7.5). A classical algorithm; no quantum hardware or speedup.

Every enhancement is behind a flag (needed for the ablation): init sobol|uniform, mbest rank|uniform,
alpha_mode linear|adaptive|fixed, diversity re-init, tunneling, QUBO slot, LS + Lamarck.
"""
import time

import numpy as np

from qflux.config import load_config
from qflux.core.encoding import encode_perm, spv_decode

from .swarm import KeySwarm
from .tunneling import tunnel


def qpso_positions(X, P, fP, G, alpha_i, mbest_mode, rng):
    N, D = X.shape
    if mbest_mode == "rank":
        ranks = np.argsort(np.argsort(fP))            # 0 = best
        w = 1.0 / (1.0 + ranks)
        w /= w.sum()
        mbest = w @ P
    else:
        mbest = P.mean(axis=0)
    phi = rng.random((N, D))
    attractor = phi * P + (1.0 - phi) * G
    u = np.clip(rng.random((N, D)), 1e-12, 1.0)
    sign = np.where(rng.random((N, D)) < 0.5, 1.0, -1.0)
    return attractor + sign * alpha_i[:, None] * np.abs(mbest - X) * np.log(1.0 / u)


def dispatch_cost_matrix(ev) -> np.ndarray:
    """Static weighted leg cost at the dispatch slot (used only to build route QUBOs)."""
    from qflux.core.split import interp
    s, s1, lam = interp(ev.centers, ev.tau0)
    T = (1 - lam) * ev.Ts[s] + lam * ev.Ts[s1]
    D = (1 - lam) * ev.Ds[s] + lam * ev.Ds[s1]
    E = (1 - lam) * ev.Es[s] + lam * ev.Es[s1]
    C = np.maximum(T - ev.T0, 0.0)
    return ev.wv[0] * T / ev.rv[0] + ev.wv[1] * D / ev.rv[1] + ev.wv[2] * C / ev.rv[2] + ev.wv[3] * E / ev.rv[3]


class QPSO(KeySwarm):
    name = "qpso"
    defaults = {"memetic": True}

    def __init__(self, **params):
        cfg = load_config()["qpso"]
        base = {k: v for k, v in cfg.items()}
        base["tunneling"] = dict(cfg["tunneling"], **params.pop("tunneling", {}))
        base["qubo_slot"] = dict(cfg["qubo_slot"], **params.pop("qubo_slot", {}))
        super().__init__(**{**base, **params})
        self._qubo_dist = None
        self._qubo_route_s = 0.15            # running estimate of seconds per route solve (D31)
        if self.p["qubo_slot"].get("enabled"):
            # import the sampler at construction, before any run clock starts: the first neal call in a
            # process otherwise pays the import inside the time budget (found by the D31 deadline test)
            from dwave.samplers import SimulatedAnnealingSampler  # noqa: F401

    def alpha(self, fX, t, T_est):
        p = self.p
        amax, amin = float(p["alpha_max"]), float(p["alpha_min"])
        N = len(fX)
        if p["alpha_mode"] == "fixed":
            return np.full(N, float(p["alpha_fixed"]))
        if p["alpha_mode"] == "adaptive":
            fmin, fmax = fX.min(), fX.max()
            return amin + (amax - amin) * (fX - fmin) / (fmax - fmin + 1e-12)
        frac = self._progress if self._progress is not None else min(t / max(T_est, 1), 1.0)
        return np.full(N, amax - (amax - amin) * frac)

    def update(self, X, P, fP, fX, G, t, T_est, rng):
        return qpso_positions(X, P, fP, G, self.alpha(fX, t, T_est), self.p["mbest"], rng)

    # ---- quantum-inspired extras --------------------------------------------------------------------
    def qubo_slot(self, st, ev, rng):
        q = self.p["qubo_slot"]
        from qflux.quantum.backends import solve_route_order
        if self._qubo_dist is None:
            self._qubo_dist = dispatch_cost_matrix(ev)
        routes = ev.decode_routes(st.best_perm) if st.best_routes is None else [list(r) for r in st.best_routes]
        changed = False
        for k, r in enumerate(routes):
            if 2 < len(r) <= int(q["max_stops"]):
                if st.deadline is not None and st.deadline - time.time() < 1.5 * self._qubo_route_s:
                    st.meta["qubo_skipped_time"] = st.meta.get("qubo_skipped_time", 0) + 1
                    break                         # too little time left for another route (D31)
                t_r = time.time()
                out = solve_route_order(r, self._qubo_dist, q["backend"], num_reads=int(q["num_reads"]),
                                        seed=int(rng.integers(2**31)))
                self._qubo_route_s = 0.7 * self._qubo_route_s + 0.3 * (time.time() - t_r)
                if out["feasible"] and ev.route_cost(out["order"]) < ev.route_cost(r) - 1e-12:
                    routes[k] = out["order"]
                    changed = True
        st.meta["qubo_calls"] = st.meta.get("qubo_calls", 0) + 1
        if changed:
            st.meta["qubo_improvements"] = st.meta.get("qubo_improvements", 0) + 1
            before = st.best_F
            st.offer_routes(routes, ev)
            if st.best_F < before and self.p.get("lamarck", True):   # write back into the best particle
                i = int(np.argmin(st.fP))
                keys = encode_perm(st.best_perm, rng)
                st.P[i] = keys
                st.X[i] = keys
                st.fP[i] = min(st.fP[i], st.best_F)

    def after_iteration(self, st, ev, rng, t):
        p = self.p
        q = p["qubo_slot"]
        if q.get("enabled") and t > 0 and t % int(q["every"]) == 0 and not st.over_budget():
            self.qubo_slot(st, ev, rng)
        tun = p["tunneling"]
        if tun.get("enabled") and st.stagnation + 1 >= int(tun["stagnation"]) and not st.over_budget():
            cand, f, kind = tunnel(st.best_perm, st.best_F, ev, rng, int(tun["trials"]), float(tun["kappa"]),
                                   stop=st.over_budget)
            if cand is not None:
                w = int(np.argmax(st.fP))                 # only the worst particle is overwritten
                keys = encode_perm(cand, rng)
                st.X[w] = keys
                st.P[w] = keys
                st.fP[w] = f
                st.offer(cand, f)                         # G changes only if strictly better (elitism)
            st.meta["tunnel_events"].append({"iter": t, "kind": kind, "F": None if f is None else float(f)})
            st.stagnation = -1                            # reset (incremented to 0 by the loop)
        delta = float(p.get("diversity_delta", 0) or 0)
        if delta > 0 and st.fX.std() < delta * abs(st.fX.mean()):
            k = max(1, int(round(float(p["reinit_frac"]) * len(st.fX))))
            worst = np.argsort(st.fX)[-k:]
            st.X[worst] = rng.random((k, st.X.shape[1]))      # X only, never P
            st.meta["reinits"] = st.meta.get("reinits", 0) + 1

    def final_polish(self, st, ev, rng):
        super().final_polish(st, ev, rng)
        if self.p["qubo_slot"].get("enabled") and not st.out_of_time():
            self.qubo_slot(st, ev, rng)


BASE_QPSO = dict(init="uniform", mbest="uniform", alpha_mode="linear", alpha_max=1.0, alpha_min=0.5,
                 memetic=False, diversity_delta=0.0, tunneling={"enabled": False}, qubo_slot={"enabled": False})
