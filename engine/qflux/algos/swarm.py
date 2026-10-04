"""Shared random-key swarm pipeline for QPSO and PSO (§7.5.3, §7.8).

Both use the same decoder (Split), evaluation counting, LS schedule, Lamarckian write-back, callbacks and
stopping rules, so a QPSO-vs-PSO comparison isolates the position-update rule.

- Rank re-normalisation (D32): after every position update X_i <- (rank(X_i) + 0.5) / n. Order-preserving,
  so every decoded tour is unchanged; it keeps keys bounded (random-key decoding has no restoring force on
  the key scale, and without it keys diverged to |X| ~ 1e4-1e5).
- LS (D28): gbest every `ls_every` iterations (all operators) and, if `memetic`, every particle whose pbest
  improved this iteration (2-opt + relocate + swap), capped at the best ceil(memetic_frac * N). LS moves are
  scored with route costs and are not counted as evaluations; `ls_calls` is reported in meta.
- Deadlines (D31): LS, final polish and every subclass hook get `st.deadline` and stop when it passes.
"""
import math
import time
import warnings

import numpy as np

from qflux.core.encoding import encode_perm, spv_decode
from qflux.core.localsearch import MEMETIC_OPS, improve_routes
from qflux.types import Solution


def rank_normalise(X: np.ndarray) -> np.ndarray:
    """Row-wise (rank + 0.5) / n: same order (so the same decoded tour), keys in (0, 1)."""
    n = X.shape[1]
    return (np.argsort(np.argsort(X, axis=1, kind="stable"), axis=1, kind="stable") + 0.5) / n


class KeySwarm:
    name = "swarm"
    defaults: dict = {"rank_renorm": True, "memetic": False, "memetic_frac": 0.25}

    def __init__(self, **params):
        self.p = {**KeySwarm.defaults, **self.defaults, **params}
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

    def ls_particle(self, st: "State", ev, rng, i: int, ops) -> bool:
        """LS on particle i's pbest with Lamarckian write-back to X and P. Returns True if improved."""
        routes = ev.decode_routes(spv_decode(st.P[i]))
        new = improve_routes(routes, ev, ops, deadline=st.deadline)
        st.meta["ls_calls"] += 1
        f = ev.routes_F(new)                         # uncounted (D28)
        if f < st.fP[i] - 1e-12:
            perm = np.array([c for r in new for c in r], dtype=np.int64)
            if self.p.get("lamarck", True):
                keys = encode_perm(perm, rng)
                st.P[i] = keys
                st.X[i] = keys
                st.fP[i] = f
                st.fX[i] = f
            st.offer_routes(new, ev)
            return True
        return False

    def polish(self, st: "State", ev, rng):
        """Full LS on gbest every `ls_every` iterations."""
        self.ls_particle(st, ev, rng, int(np.argmin(st.fP)), ("2opt", "oropt", "relocate", "swap"))

    def memetic(self, st: "State", ev, rng, improved: np.ndarray):
        """LS on particles whose pbest improved this iteration, best ceil(frac * N) first (D28)."""
        if improved.size == 0:
            return
        cap = max(1, math.ceil(float(self.p["memetic_frac"]) * len(st.fP)))
        for i in improved[np.argsort(st.fP[improved])][:cap]:
            if st.out_of_time():
                break
            self.ls_particle(st, ev, rng, int(i), MEMETIC_OPS)

    # ---- main loop ---------------------------------------------------------------------------------
    def run(self, ev, budget_evals: int | None, budget_s: float | None, rng, callback=None, should_stop=None,
            init_keys: np.ndarray | None = None) -> tuple[Solution, list[tuple[int, float]]]:
        n = ev.inst.n
        N = int(self.p.get("N", 40))
        st = State(ev, budget_evals, budget_s)
        self.setup(n, rng)
        st.X = self.init_positions(N, n, rng, init_keys)
        if self.p.get("rank_renorm", True):
            st.X = rank_normalise(st.X)
        st.fX = np.full(N, np.inf)
        for i in range(N):
            if i and st.over_budget():
                break
            st.fX[i] = st.eval_keys(st.X[i])
        st.P, st.fP = st.X.copy(), st.fX.copy()
        T_est = self.estimate_iterations(budget_evals, N)
        ls_every = int(self.p.get("ls_every", 0) or 0)
        t = 0
        partial = False
        while not st.over_budget():
            if should_stop is not None and should_stop():
                partial = True
                break
            G = st.P[int(np.argmin(st.fP))]
            self._progress = st.progress()
            st.X = self.update(st.X, st.P, st.fP, st.fX, G, t, T_est, rng)
            if self.p.get("rank_renorm", True):
                st.X = rank_normalise(st.X)
            st.meta["max_abs_key"] = max(st.meta["max_abs_key"], float(np.abs(st.X).max()))
            improved = []
            for i in range(N):
                if st.over_budget():
                    break
                st.fX[i] = st.eval_keys(st.X[i])
                if st.fX[i] < st.fP[i]:
                    st.P[i] = st.X[i]
                    st.fP[i] = st.fX[i]
                    improved.append(i)
            if ls_every and self.p.get("memetic") and not st.out_of_time():
                self.memetic(st, ev, rng, np.array(improved, dtype=np.int64))
            if ls_every and t % ls_every == 0 and not st.out_of_time():
                self.polish(st, ev, rng)
            self.after_iteration(st, ev, rng, t)
            st.stagnation = 0 if st.best_F < st.last_best - 1e-12 else st.stagnation + 1
            st.last_best = st.best_F
            st.curve.append((ev.evals, st.best_F))
            if callback is not None and t % 5 == 0:
                callback({"iter": t, "evals": ev.evals, "best_F": st.best_F, "elapsed_s": time.time() - st.t0})
            t += 1
        if not partial and st.time_left_frac() > 0.01:
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
            routes = improve_routes(ev.decode_routes(st.best_perm) if st.best_routes is None else st.best_routes,
                                    ev, deadline=st.deadline)
            st.meta["ls_calls"] += 1
            st.offer_routes(routes, ev)

    @staticmethod
    def estimate_iterations(budget_evals, N):
        return max(1, int(budget_evals // N)) if budget_evals else 300


class State:
    def __init__(self, ev, budget_evals, budget_s):
        self.ev, self.budget_evals, self.budget_s = ev, budget_evals, budget_s
        self.t0 = time.time()
        self.deadline = self.t0 + budget_s if budget_s is not None else None
        self.best_F = np.inf
        self.best_perm = None
        self.best_routes = None
        self.last_best = np.inf
        self.stagnation = 0
        self.improved = False
        self.curve: list[tuple[int, float]] = []
        self.meta: dict = {"tunnel_events": [], "ls_calls": 0, "max_abs_key": 0.0}

    def out_of_time(self) -> bool:
        return self.deadline is not None and time.time() >= self.deadline

    def time_left_frac(self) -> float:
        """Share of the time budget still left (1.0 without a time budget)."""
        if self.deadline is None:
            return 1.0
        return max(0.0, (self.deadline - time.time()) / self.budget_s)

    def over_budget(self) -> bool:
        if self.budget_evals is not None and self.ev.evals >= self.budget_evals:
            return True
        return self.out_of_time()

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
