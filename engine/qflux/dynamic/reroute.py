"""Dynamic re-optimisation after a simulated incident (§7.10, REQ-12).

1. Plan at tau0 and simulate the clock. 2. At incident time t_inc every vehicle is at, or heading to, a
known next stop (that leg is committed). 3. Vehicles whose remaining road path crosses an incident edge:
(a) road-level detour — legs are recomputed on the incident-aware matrices; (b) remaining stops are
re-sequenced from the committed stop back to the depot (Held-Karp if <= 12 stops, else 2-opt).
4. Unaffected vehicles are unchanged. 5. Next dispatch wave: warm-started solve. 6. Accept rule: keep the
new routes only if they cost less than the old routes re-evaluated under the new traffic.
"""
import itertools
import time

import numpy as np

from qflux.explain.templates import reroute_sentences
from qflux.traffic import events
from qflux.traffic.profiles import slot_weights
from qflux.traffic.route_eval import evaluate_routes, fitness, route_legs
from qflux.traffic.td_matrix import TDBundle
from qflux.types import Instance, Refs, Weights


def _snapshot(bundle: TDBundle, t: float) -> np.ndarray:
    s, s1, lam = slot_weights(t, bundle.slot_centers)
    return (1 - lam) * bundle.T_slots[s] + lam * bundle.T_slots[s1]


def held_karp_path(start: int, stops: list[int], C: np.ndarray, end: int = 0) -> list[int]:
    """Exact order of `stops` for a path start -> stops -> end (O(m^2 2^m), m <= 12)."""
    m = len(stops)
    if m <= 1:
        return list(stops)
    dp = {(1 << k, k): (C[start, stops[k]], -1) for k in range(m)}
    for size in range(2, m + 1):
        for subset in itertools.combinations(range(m), size):
            mask = sum(1 << k for k in subset)
            for k in subset:
                prev_mask = mask ^ (1 << k)
                dp[(mask, k)] = min(((dp[(prev_mask, j)][0] + C[stops[j], stops[k]], j)
                                     for j in subset if j != k), key=lambda x: x[0])
    full = (1 << m) - 1
    last = min(range(m), key=lambda k: dp[(full, k)][0] + C[stops[k], end])
    order, mask = [], full
    while last != -1:
        order.append(stops[last])
        _, prv = dp[(mask, last)]
        mask ^= 1 << last
        last = prv
    return order[::-1]


def two_opt_path(start: int, stops: list[int], C: np.ndarray, end: int = 0) -> list[int]:
    seq = [start] + list(stops) + [end]
    improved = True
    while improved:
        improved = False
        for i in range(1, len(seq) - 2):
            for j in range(i + 1, len(seq) - 1):
                d = (C[seq[i - 1], seq[j]] + C[seq[i], seq[j + 1]]) - (C[seq[i - 1], seq[i]] + C[seq[j], seq[j + 1]])
                if d < -1e-9:
                    seq[i:j + 1] = seq[i:j + 1][::-1]
                    improved = True
    return seq[1:-1]


def resequence(start: int, stops: list[int], C: np.ndarray) -> list[int]:
    return held_karp_path(start, stops, C) if len(stops) <= 12 else two_opt_path(start, stops, C)


def no_reroute_bundle(old: TDBundle, new: TDBundle) -> TDBundle:
    """Old road paths, new traffic: what vehicles experience if nobody re-routes (the baseline)."""
    from qflux.traffic.emissions import edge_co2_kg
    from qflux.traffic.fleet_eq import path_sums
    from qflux.traffic.td_matrix import edge_times
    per_slot = events.slot_incidents(new.incidents, new.slot_centers)
    T, E = np.zeros_like(old.T_slots), np.zeros_like(old.E_slots)
    for s, c in enumerate(old.slot_centers):
        te = edge_times(new.net, c, inc_factor=events.factor_for(new.net, per_slot[s]))
        T[s] = path_sums(old.paths[s], old.m, te)
        E[s] = path_sums(old.paths[s], old.m, edge_co2_kg(new.net.length_km, te))
    return TDBundle(old.net, old.terminals, old.slot_centers, T, old.D_slots, E, old.T0, old.T0_path,
                    old.paths, new.incidents)


def vehicle_state(inst: Instance, bundle: TDBundle, route: list[int], t_inc: float):
    """(done, committed, remaining, remaining_legs) at t_inc on the old plan."""
    legs = route_legs(inst, bundle, route)
    stops = list(route)
    for k, leg in enumerate(legs):
        arrive = leg["depart"] + leg["T"]
        if arrive > t_inc:                     # leg k is in progress (or not started) at t_inc
            if leg["j"] == 0:                  # already heading home
                return stops, None, [], legs[k:]
            done = stops[:k]
            return done, stops[k], stops[k + 1:], legs[k:]
    return stops, None, [], []


def reroute(inst: Instance, old: TDBundle, new: TDBundle, routes: list[list[int]], t_inc: float,
            w: Weights, refs: Refs) -> dict:
    t = time.time()
    inc_edges = set()
    for inc in new.incidents:
        inc_edges.update(events.affected_edges(new.net, inc).tolist())
    C_new = _snapshot(new, t_inc)
    new_routes, eta = [], []
    for v, r in enumerate(routes):
        done, committed, remaining, legs = vehicle_state(inst, old, r, t_inc)
        affected = False
        for leg in legs:
            s, s1, lam = slot_weights(leg["depart"], old.slot_centers)
            path = old.path(s if lam < 0.5 else s1, leg["i"], leg["j"])
            if inc_edges.intersection(path.tolist()):
                affected = True
                break
        if affected and committed is not None and len(remaining) > 1:
            nr = done + [committed] + resequence(committed, remaining, C_new)
        else:
            nr = list(r)
        new_routes.append(nr)
        eta.append(dict(vehicle=v + 1, affected=bool(affected)))
    ev_old_old = evaluate_routes(inst, old, routes, w, refs)
    ev_old_new = evaluate_routes(inst, new, routes, w, refs)             # detour only (a)
    norr = no_reroute_bundle(old, new)
    ev_norr = evaluate_routes(inst, norr, routes, w, refs)   # nobody re-routes
    ev_new_new = evaluate_routes(inst, new, new_routes, w, refs)
    # accept rule: re-sequenced routes only if cheaper than the old sequence under the new traffic
    accepted = ev_new_new["F"] < ev_old_new["F"] - 1e-12
    final = new_routes if accepted else [list(r) for r in routes]
    ev_final = ev_new_new if accepted else ev_old_new
    if ev_final["F"] >= ev_norr["F"]:          # never report a plan worse than not re-routing at all
        ev_final = ev_norr
    for e, a, n, c in zip(eta, ev_old_old["routes"], ev_norr["routes"], ev_final["routes"]):
        e.update(before_min=round(float(a["ret"]), 2), no_reroute_min=round(float(n["ret"]), 2),
                 after_min=round(float(c["ret"]), 2))
    report = dict(accepted=bool(ev_final is not ev_norr), t_inc=t_inc,
                  resequenced=bool(accepted),
                  delay_increase_min=round(float(ev_norr["T"] - ev_old_old["T"]), 3),
                  delay_avoided_min=round(float(ev_norr["T"] - ev_final["T"]), 3),
                  F_no_reroute=round(float(ev_norr["F"]), 6),
                  F_final=round(float(ev_final["F"]), 6),
                  reopt_time_s=round(time.time() - t, 3), eta_change=eta)
    report["sentences"] = reroute_sentences(report)
    final_bundle = norr if ev_final is ev_norr else new
    return dict(routes=final, report=report, ev_old_old=ev_old_old, ev_final=ev_final, bundle=final_bundle)


def warm_vs_cold(inst_new: Instance, w: Weights, refs: Refs, warm_routes, time_s: float = 5.0, seed: int = 0):
    """Next dispatch wave: warm-started vs cold solve on the incident-aware instance (convergence curves)."""
    from .solver import solve
    cold = solve(inst_new, w, refs, algorithm="qpso", seed=seed, budget={"time_s": time_s})
    warm = solve(inst_new, w, refs, algorithm="qpso", seed=seed, budget={"time_s": time_s / 3.0},
                 warm_start_perm=[c for r in warm_routes for c in r], warm_start_routes=warm_routes)
    return dict(cold=cold, warm=warm)
