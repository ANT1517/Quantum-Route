"""Shared random-key swarm pipeline for QPSO and PSO (§7.5.3, §7.8).

Both use the same decoder (Split), evaluation counting, LS schedule, Lamarckian write-back, callbacks and
stopping rules, so a QPSO-vs-PSO comparison isolates the position-update rule.
"""
import time
import warnings

import numpy as np

from qflux.core.encoding import encode_perm, spv_decode
from qflux.core.localsearch import improve_routes
from qflux.types import Solution


class KeySwarm:
    name = "swarm"
    defaults: dict = {}

    def __init__(self, **params):
        self.p = {**self.defaults, **params}
        self._progress = None        # fraction of the budget used (evals or time), set each iteration

    # ---- hooks -----------------------------------------------------------------------------------
    def setup(self, n: int, rng):
        pass

    def update(self, X, P, fP, fX, G, t, T_est, rng) -> np.ndarray:
        raise NotImplementedError

    def after_iteration(self, st: "State", ev, rng, t: int):
        pass

    # ---- helpers ---------------------------------------------------------------------------------
    def init_positions(self, N, n, rng, init_keys):
        if self.p.get("init") == "sobol":
            from scipy.stats import qmc
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                X = qmc.Sobol(d=n, scramble=True, seed=rng).random(N)
        else:
            X = rng.random((N, n))
        if init_keys is not None:                    # warm start: 50% previous best + noise (§7.10)
            h = max(1, N // 2)
            X[:h] = init_keys[None, :] + rng.normal(0, 0.05, (h, n))
            X[0] = init_keys
        return X

    def polish(self, st: "State", ev, rng, final: bool = False):
        """LS on gbest (+ top pbests) with Lamarckian write-back."""
        k_top = int(self.p.get("ls_top_pbests", 0))
        idx = [int(np.argmin(st.fP))] + [int(i) for i in np.argsort(st.fP)[1:1 + k_top]]
        for i in dict.fromkeys(idx):
            routes = ev.decode_routes(spv_decode(st.P[i]))
            new = improve_routes(routes, ev)
            perm = np.array([c for r in new for c in r], dtype=np.int64)
            f = ev.fitness_perm(perm)
            if f < st.fP[i] - 1e-12:
                if self.p.get("lamarck", True):
                    keys = encode_perm(perm, rng)
                    st.P[i] = keys
                    st.X[i] = keys
                    st.fP[i] = f
                st.offer(perm, f)
            if st.over_budget():
                break

    # ---- main loop ---------------------------------------------------------------------------------
    def run(self, ev, budget_evals: int | None, budget_s: float | None, rng, callback=None, should_stop=None,
            init_keys: np.ndarray | None = None) -> tuple[Solution, list[tuple[int, float]]]:
        n = ev.inst.n
        N = int(self.p.get("N", 40))
        st = State(ev, budget_evals, budget_s)
        self.setup(n, rng)
        st.X = self.init_positions(N, n, rng, init_keys)
        st.fX = np.array([st.eval_keys(x) for x in st.X])
        st.P, st.fP = st.X.copy(), st.fX.copy()
        T_est = self.estimate_iterations(budget_evals, N)
        t = 0
        partial = False
        while not st.over_budget():
            if should_stop is not None and should_stop():
                partial = True
                break
            G = st.P[int(np.argmin(st.fP))]
            self._progress = st.progress()
            st.X = self.update(st.X, st.P, st.fP, st.fX, G, t, T_est, rng)
            for i in range(N):
                if st.over_budget():
                    break
                st.fX[i] = st.eval_keys(st.X[i])
                if st.fX[i] < st.fP[i]:
                    st.P[i] = st.X[i]
                    st.fP[i] = st.fX[i]
            st.improved = st.best_F < st.last_best - 1e-12
            ls_every = int(self.p.get("ls_every", 0) or 0)
            if ls_every and t % ls_every == 0 and not st.over_budget():
                self.polish(st, ev, rng)
            self.after_iteration(st, ev, rng, t)
            st.stagnation = 0 if st.best_F < st.last_best - 1e-12 else st.stagnation + 1
            st.last_best = st.best_F
            st.curve.append((ev.evals, st.best_F))
            if callback is not None and t % 5 == 0:
                callback({"iter": t, "evals": ev.evals, "best_F": st.best_F, "elapsed_s": time.time() - st.t0})
            t += 1
        if not partial:
            self.final_polish(st, ev, rng)
        sol = ev.solution(st.best_perm)
        if sol.F > st.best_F + 1e-9:     # best found via route-level moves not reproduced by Split
            sol = ev.solution_from_routes(st.best_routes or ev.decode_routes(st.best_perm))
        sol.meta.update(dict(algo=self.name, iterations=t, evals=ev.evals, wall_s=time.time() - st.t0,
                             partial=partial, **st.meta))
        st.curve.append((ev.evals, min(st.best_F, sol.F)))
        return sol, st.curve

    def final_polish(self, st, ev, rng):
        if int(self.p.get("ls_every", 0) or 0):
            routes = improve_routes(ev.decode_routes(st.best_perm), ev)
            st.offer_routes(routes, ev)

    @staticmethod
    def estimate_iterations(budget_evals, N):
        return max(1, int(budget_evals // N)) if budget_evals else 300


class State:
    def __init__(self, ev, budget_evals, budget_s):
        self.ev, self.budget_evals, self.budget_s = ev, budget_evals, budget_s
        self.t0 = time.time()
        self.best_F = np.inf
        self.best_perm = None
        self.best_routes = None
        self.last_best = np.inf
        self.stagnation = 0
        self.improved = False
        self.curve: list[tuple[int, float]] = []
        self.meta: dict = {"tunnel_events": []}

    def over_budget(self) -> bool:
        if self.budget_evals is not None and self.ev.evals >= self.budget_evals:
            return True
        return self.budget_s is not None and time.time() - self.t0 >= self.budget_s

    def progress(self) -> float | None:
        """Fraction of the budget used, so schedules follow time budgets as well as evaluation budgets."""
        fr = []
        if self.budget_evals:
            fr.append(self.ev.evals / self.budget_evals)
        if self.budget_s:
            fr.append((time.time() - self.t0) / self.budget_s)
        return min(max(fr), 1.0) if fr else None

    def eval_keys(self, x) -> float:
        perm = spv_decode(x)
        f = self.ev.fitness_perm(perm)
        self.offer(perm, f)
        return f

    def offer(self, perm, f):
        if f < self.best_F:
            self.best_F, self.best_perm, self.best_routes = f, np.asarray(perm, np.int64).copy(), None

    def offer_routes(self, routes, ev):
        F = ev.routes_F(routes)
        if F < self.best_F - 1e-12:
            self.best_F = F
            self.best_perm = np.array([c for r in routes for c in r], dtype=np.int64)
            self.best_routes = [list(r) for r in routes]
