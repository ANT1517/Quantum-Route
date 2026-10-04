"""QUBO slot validation (§7.7.4): neal (classical simulated annealing on the route QUBO) vs brute force vs 2-opt.

    python scripts/run_qubo_check.py [--num-reads 200] [--hyd-time-s 20]

Routes with 3..7 stops from
  * best-known solutions of the Augerat A instances (the .sol files; instance distances), and
  * QPSO-full solutions on Hyderabad (dispatch-slot travel times, minutes):
      Hyderabad-60 (K = 6, Q = 200, the demo scenario) and Hyderabad-60-K12 (K = 12, Q = 100, stated variant
      with shorter routes so more of them have <= 7 stops).
Penalty sweep A in {1.5, 3, 6} x max d within the route. Brute force gives the optimum (m <= 7).

Writes results/tables/qubo_validation.csv (one row per source x A: routes, feasibility rate, % routes where
neal = optimum, mean/max gap to optimum for neal and 2-opt, time per route) and
results/tables/qubo_validation_routes.csv (one row per route x A). Classical sampler: this measures
readiness of the formulation, not quantum advantage (§1.4). Run on an idle machine (it reports times).
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from qflux.bench.harness import keep_awake, machine_info  # noqa: E402
from qflux.bench.loader import load_instance, read_solution_routes  # noqa: E402
from qflux.quantum.backends import solve_route_order  # noqa: E402
from qflux.quantum.qubo_route import tour_cost  # noqa: E402

A_INSTANCES = ["A-n32-k5", "A-n44-k6", "A-n63-k9", "A-n69-k9", "A-n80-k10"]
A_FACTORS = (1.5, 3.0, 6.0)
TOL = 1e-9


def cvrplib_routes():
    for name in A_INSTANCES:
        inst = load_instance(name)
        for r in read_solution_routes(name):
            if 3 <= len(r) <= 7:
                yield f"CVRPLIB A (BKS routes)", name, list(r), inst.D


def hyderabad_routes(time_s: float):
    from qflux import api as engine
    from qflux.core.construct import dispatch_matrix
    for label, spec in (("Hyderabad-60", {"source": "hyderabad", "n_customers": 60, "K": 6, "Q": 200, "seed": 7,
                                          "tau0": 1050}),
                        ("Hyderabad-60-K12", {"source": "hyderabad", "n_customers": 60, "K": 12, "Q": 100, "seed": 7,
                                              "tau0": 1050})):
        res = engine.run_job(spec, {"algorithm": "qpso", "weights": {"wT": 0.5, "wD": 0.2, "wC": 0.2, "wE": 0.1},
                                    "seed": 1, "budget": {"time_s": time_s}})
        inst = engine.build_instance(spec)
        dist = np.asarray(dispatch_matrix(inst), float)
        for route in res["routes"]:
            stops = [int(c) for c in route["stops"]]
            if 3 <= len(stops) <= 7:
                yield f"Hyderabad (QPSO-full routes, {label})", label, stops, dist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--num-reads", type=int, default=200)
    ap.add_argument("--hyd-time-s", type=float, default=20.0)
    a = ap.parse_args()
    keep_awake(True)
    rows = []
    routes = list(cvrplib_routes()) + list(hyderabad_routes(a.hyd_time_s))
    for k, (source, inst_name, route, dist) in enumerate(routes):
        nodes = [0] + route
        dmax = float(dist[np.ix_(nodes, nodes)].max())
        t = time.perf_counter(); opt = solve_route_order(route, dist, "brute"); t_brute = time.perf_counter() - t
        t = time.perf_counter(); two = solve_route_order(route, dist, "2opt"); t_2opt = time.perf_counter() - t
        c_opt, c_2opt = tour_cost(opt["order"], dist), tour_cost(two["order"], dist)
        for f in A_FACTORS:
            t = time.perf_counter()
            ne = solve_route_order(route, dist, "neal", num_reads=a.num_reads, A=f * dmax, seed=1000 + k)
            t_neal = time.perf_counter() - t
            c_neal = tour_cost(ne["order"], dist) if ne["feasible"] else None
            rows.append({"source": source, "instance": inst_name, "route_id": k, "m": len(route), "A_factor": f,
                         "neal_feasible": ne["feasible"],
                         "neal_optimal": bool(ne["feasible"] and c_neal <= c_opt * (1 + TOL) + TOL),
                         "neal_gap_pct": None if c_neal is None else 100 * (c_neal - c_opt) / c_opt,
                         "twoopt_optimal": bool(c_2opt <= c_opt * (1 + TOL) + TOL),
                         "twoopt_gap_pct": 100 * (c_2opt - c_opt) / c_opt,
                         "time_neal_s": t_neal, "time_brute_s": t_brute, "time_2opt_s": t_2opt})
        print(f"[{k + 1}/{len(routes)}] {inst_name} m={len(route)}")
    df = pd.DataFrame(rows)
    out_dir = ROOT / "results" / "tables"
    df.to_csv(out_dir / "qubo_validation_routes.csv", index=False, float_format="%.6g")
    summ = []
    for (source, f), g in df.groupby(["source", "A_factor"], sort=False):
        feas = g[g.neal_feasible]
        summ.append({"source": source, "A_factor_x_max_d": f, "routes": len(g), "m_range": f"{g.m.min()}-{g.m.max()}",
                     "num_reads": a.num_reads,
                     "neal_feasible_pct": 100 * g.neal_feasible.mean(),
                     "neal_optimal_pct": 100 * g.neal_optimal.mean(),
                     "neal_mean_gap_pct_feasible": feas.neal_gap_pct.mean() if len(feas) else None,
                     "neal_max_gap_pct_feasible": feas.neal_gap_pct.max() if len(feas) else None,
                     "twoopt_optimal_pct": 100 * g.twoopt_optimal.mean(),
                     "twoopt_mean_gap_pct": g.twoopt_gap_pct.mean(),
                     "time_per_route_neal_ms": 1e3 * g.time_neal_s.mean(),
                     "time_per_route_brute_ms": 1e3 * g.time_brute_s.mean(),
                     "time_per_route_2opt_ms": 1e3 * g.time_2opt_s.mean()})
    pd.DataFrame(summ).to_csv(out_dir / "qubo_validation.csv", index=False, float_format="%.6g")
    (out_dir / "qubo_validation_meta.json").write_text(pd.Series({
        "note": "Classical simulated annealing (dwave-samplers) on the route QUBO; readiness, not quantum advantage.",
        "brute_force": "exact optimum for m <= 7", "machine": machine_info()}).to_json(indent=2), encoding="utf-8")
    print(pd.DataFrame(summ).round(3).to_string(index=False))
    keep_awake(False)


if __name__ == "__main__":
    main()
