"""Simulated annealing baseline on giant tours (§7.8): 2-opt / relocate / swap moves, each move = 1
evaluation, geometric cooling with T0 tuned to ~30% initial acceptance of worsening moves."""
import time

import numpy as np

from qflux.config import load_config

from .curve import TimeCurve


def neighbour(perm: np.ndarray, rng) -> np.ndarray:
    p = perm.copy()
    n = len(p)
    i, j = sorted(rng.choice(n, 2, replace=False))
    k = rng.integers(3)
    if k == 0:
        p[i:j + 1] = p[i:j + 1][::-1]
    elif k == 1:
        c = p[i]
        p = np.insert(np.delete(p, i), j, c)
    else:
        p[i], p[j] = p[j], p[i]
    return p


class SA:
    name = "sa"

    def __init__(self, **params):
        self.p = {**load_config()["sa"], "N": 40, **params}   # no +LS variant: SA is already a local search (D28)

    def run(self, ev, budget_evals, budget_s, rng, callback=None, should_stop=None, init_keys=None):
        p = self.p
        n = ev.inst.n
        t0 = time.time()
        budget = budget_evals or 12000

        def over():
            return (budget_evals is not None and ev.evals >= budget_evals) or \
                   (budget_s is not None and time.time() - t0 >= budget_s)

        cur = np.argsort(init_keys) + 1 if init_keys is not None else rng.permutation(n) + 1
        fc = ev.fitness_perm(cur)
        best, fb = cur.copy(), fc
        # calibrate T0: mean worsening over 50 random moves -> accept ~initial_accept of them
        deltas = []
        for _ in range(50):
            f = ev.fitness_perm(neighbour(cur, rng))
            if f > fc:
                deltas.append(f - fc)
        mean_d = np.mean(deltas) if deltas else 1e-3
        T = -mean_d / np.log(float(p["initial_accept"]))
        T_end = T * 1e-3
        T_start, e_start = T, ev.evals
        n_moves = max(1, budget - ev.evals) if budget_evals else None

        def progress():
            # cooling follows the fraction of the budget used (evaluations or wall time)
            fr = []
            if n_moves:
                fr.append((ev.evals - e_start) / n_moves)
            if budget_s:
                fr.append((time.time() - t0) / budget_s)
            return min(max(fr), 1.0) if fr else min(k / 100000, 1.0)
        curve, k, partial = [], 0, False
        ct = TimeCurve(t0)
        ct.add(float(fb))
        while not over():
            if should_stop is not None and should_stop():
                partial = True
                break
            cand = neighbour(cur, rng)
            f = ev.fitness_perm(cand)
            if f < fc or rng.random() < np.exp(-(f - fc) / max(T, 1e-300)):
                cur, fc = cand, f
                if f < fb:
                    best, fb = cand.copy(), f
                    ct.add(float(fb))
            T = T_start * (T_end / T_start) ** progress()
            k += 1
            if k % int(p["N"]) == 0:
                curve.append((ev.evals, float(fb)))
                if callback is not None and (k // int(p["N"])) % 5 == 0:
                    callback({"iter": k // int(p["N"]), "evals": ev.evals, "best_F": float(fb),
                              "elapsed_s": time.time() - t0})
        sol = ev.solution(best)
        sol.meta.update(algo=self.name, moves=k, evals=ev.evals, wall_s=time.time() - t0, partial=partial)
        curve.append((ev.evals, float(min(fb, sol.F))))
        sol.meta["curve_t"] = ct.final(float(min(fb, sol.F)))
        return sol, curve
