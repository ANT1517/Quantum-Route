"""Genetic algorithm baseline on giant tours (§7.8): OX crossover, swap + inversion mutation, tournament 3,
elitism 2, Split decoding.

GA+LS (D28) mirrors QPSO's LS rule: LS on the best every `ls_every` generations, plus memetic LS on surviving
offspring. The GA is generational with elitism, so every offspring survives; the same ceil(25%) cap as QPSO
applies (best offspring of the generation). LS moves are uncounted; `ls_calls` is reported in meta.
Every LS call stops at the time-budget deadline (D31).
"""
import math
import time

import numpy as np

from qflux.config import load_config
from qflux.core.localsearch import MEMETIC_OPS, improve_routes

from .curve import TimeCurve


def ox(p1: np.ndarray, p2: np.ndarray, rng) -> np.ndarray:
    n = len(p1)
    i, j = sorted(rng.choice(n, 2, replace=False))
    child = np.full(n, -1, np.int64)
    child[i:j + 1] = p1[i:j + 1]
    used = set(p1[i:j + 1].tolist())
    fill = [c for c in np.concatenate([p2[j + 1:], p2[:j + 1]]) if c not in used]
    pos = [(j + 1 + k) % n for k in range(n - (j - i + 1))]
    child[pos] = fill
    return child


def mutate(perm: np.ndarray, rng) -> np.ndarray:
    perm = perm.copy()
    i, j = sorted(rng.choice(len(perm), 2, replace=False))
    if rng.random() < 0.5:
        perm[i], perm[j] = perm[j], perm[i]
    else:
        perm[i:j + 1] = perm[i:j + 1][::-1]
    return perm


class GA:
    name = "ga"

    def __init__(self, **params):
        self.p = {**load_config()["ga"], "ls_every": 0, "memetic_frac": 0.25, **params}

    def run(self, ev, budget_evals, budget_s, rng, callback=None, should_stop=None, init_keys=None):
        p = self.p
        n, pop_n = ev.inst.n, int(p["pop"])
        t0 = time.time()
        deadline = t0 + budget_s if budget_s is not None else None
        ls_calls = 0

        def out_of_time():
            return deadline is not None and time.time() >= deadline

        def over():
            return (budget_evals is not None and ev.evals >= budget_evals) or out_of_time()

        def ls(perm, f, ops):
            """LS with Lamarckian write-back -> (perm, F); F of the result is uncounted (route costs)."""
            nonlocal ls_calls
            ls_calls += 1
            routes = improve_routes(ev.decode_routes(perm), ev, ops, deadline=deadline)
            f2 = ev.routes_F(routes)
            if f2 < f - 1e-12:
                return np.array([c for r in routes for c in r], dtype=np.int64), f2
            return perm, f

        pop = [rng.permutation(n) + 1 for _ in range(pop_n)]
        if init_keys is not None:
            pop[0] = np.argsort(init_keys) + 1
        fit = np.full(pop_n, np.inf)
        for i, x in enumerate(pop):
            if i and over():
                break
            fit[i] = ev.fitness_perm(x)
        curve, gen, partial = [], 0, False
        ct = TimeCurve(t0)
        best_routes = None
        while not over():
            if should_stop is not None and should_stop():
                partial = True
                break
            order = np.argsort(fit)
            new = [pop[i].copy() for i in order[:int(p["elitism"])]]
            newf = [fit[i] for i in order[:int(p["elitism"])]]
            while len(new) < pop_n and not over():
                a = min(rng.choice(pop_n, int(p["tournament"]), replace=False), key=lambda i: fit[i])
                b = min(rng.choice(pop_n, int(p["tournament"]), replace=False), key=lambda i: fit[i])
                child = ox(pop[a], pop[b], rng) if rng.random() < p["pc"] else pop[a].copy()
                if rng.random() < p["pm"]:
                    child = mutate(child, rng)
                new.append(child)
                newf.append(ev.fitness_perm(child))
            n_elite = int(p["elitism"])
            pop, fit = new, np.array(newf)
            ls_every = int(p.get("ls_every") or 0)
            if ls_every:
                offspring = np.arange(n_elite, len(pop))
                cap = max(1, math.ceil(float(p["memetic_frac"]) * pop_n))
                for i in offspring[np.argsort(fit[offspring])][:cap]:
                    if out_of_time():
                        break
                    pop[i], fit[i] = ls(pop[i], fit[i], MEMETIC_OPS)
                if gen % ls_every == 0 and not out_of_time():
                    i = int(np.argmin(fit))
                    pop[i], fit[i] = ls(pop[i], fit[i], ("2opt", "oropt", "relocate", "swap"))
            curve.append((ev.evals, float(fit.min())))
            ct.add(float(fit.min()))
            if callback is not None and gen % 5 == 0:
                callback({"iter": gen, "evals": ev.evals, "best_F": float(fit.min()), "elapsed_s": time.time() - t0})
            gen += 1
        best = pop[int(np.argmin(fit))]
        if int(p.get("ls_every") or 0) and not partial and \
                (deadline is None or deadline - time.time() > 0.01 * budget_s):
            best_routes = improve_routes(ev.decode_routes(best), ev, deadline=deadline)
            ls_calls += 1
        sol = ev.solution_from_routes(best_routes) if best_routes else ev.solution(best)
        if best_routes and sol.F > ev.solution(best).F:
            sol = ev.solution(best)
        sol.meta.update(algo=self.name, iterations=gen, evals=ev.evals, wall_s=time.time() - t0, partial=partial,
                        ls_calls=ls_calls)
        curve.append((ev.evals, min(sol.F, float(fit.min()))))
        sol.meta["curve_t"] = ct.final(min(sol.F, float(fit.min())))
        return sol, curve
