"""Genetic algorithm baseline on giant tours (§7.8): OX crossover, swap + inversion mutation, tournament 3,
elitism 2, Split decoding. Optional +LS uses the same schedule as QPSO (LS on the best every ls_every gens)."""
import time

import numpy as np

from qflux.config import load_config
from qflux.core.localsearch import improve_routes


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
        self.p = {**load_config()["ga"], "ls_every": 0, **params}

    def run(self, ev, budget_evals, budget_s, rng, callback=None, should_stop=None, init_keys=None):
        p = self.p
        n, pop_n = ev.inst.n, int(p["pop"])
        t0 = time.time()

        def over():
            return (budget_evals is not None and ev.evals >= budget_evals) or \
                   (budget_s is not None and time.time() - t0 >= budget_s)

        pop = [rng.permutation(n) + 1 for _ in range(pop_n)]
        if init_keys is not None:
            pop[0] = np.argsort(init_keys) + 1
        fit = np.array([ev.fitness_perm(x) for x in pop])
        curve, gen, partial = [], 0, False
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
            pop, fit = new, np.array(newf)
            ls = int(p.get("ls_every") or 0)
            if ls and gen % ls == 0 and not over():
                i = int(np.argmin(fit))
                routes = improve_routes(ev.decode_routes(pop[i]), ev)
                perm = np.array([c for r in routes for c in r], dtype=np.int64)
                f = ev.fitness_perm(perm)
                if f < fit[i]:
                    pop[i], fit[i] = perm, f
            curve.append((ev.evals, float(fit.min())))
            if callback is not None and gen % 5 == 0:
                callback({"iter": gen, "evals": ev.evals, "best_F": float(fit.min()), "elapsed_s": time.time() - t0})
            gen += 1
        best = pop[int(np.argmin(fit))]
        if int(p.get("ls_every") or 0) and not partial:
            best_routes = improve_routes(ev.decode_routes(best), ev)
        sol = ev.solution_from_routes(best_routes) if best_routes else ev.solution(best)
        if best_routes and sol.F > ev.solution(best).F:
            sol = ev.solution(best)
        sol.meta.update(algo=self.name, iterations=gen, evals=ev.evals, wall_s=time.time() - t0, partial=partial)
        curve.append((ev.evals, min(sol.F, float(fit.min()))))
        return sol, curve
