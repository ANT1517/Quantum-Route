"""Regenerate the Hyderabad demo artefacts in results/demo/ with one command (Phase 7 acceptance).

    python scripts/run_fleet_demo.py [--time-s 5] [--S 25]

Writes (all numbers come from runs, never typed by hand):
    result_demo.json         Hyderabad-60 at 17:30, balanced weights (ResultJSON)
    result_0300.json         same customers planned at 03:00 (time-of-day comparison)
    fleet_demo.json          {S, modes:{naive,user_eq,system_opt: FleetResult}, msa_history}
    incident_demo.json       {incident, before, after, report, warm_vs_cold}
    shortest_path_demo.json  {source, target, labels, depart_min, incident, before, after, astar_check}
    *.geojson                route / path layers for slides and GIS
    metrics.json             headline numbers + provenance (feed for results/SLIDE_NUMBERS.md)
Until Person A's solver branch is merged the route planner is the OR-Tools stand-in; every file says
which algorithm actually ran.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

import numpy as np  # noqa: E402

from qflux import api  # noqa: E402
from qflux.config import load_config  # noqa: E402
from qflux.explain.templates import shortest_path_sentence  # noqa: E402
from qflux.traffic.hyd_graph import AREAS  # noqa: E402
from qflux.traffic.profiles import ARTERIAL  # noqa: E402
from qflux.traffic.td_matrix import bundle_for  # noqa: E402

OUT = ROOT / "results" / "demo"
BALANCED = dict(zip(("wT", "wD", "wC", "wE"), load_config()["weights_presets"]["balanced"]))
HYD = {"source": "hyderabad", "n_customers": 60, "id": "hyderabad-60"}


def dump(name: str, obj) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, indent=1, default=float), encoding="utf-8")
    print(f"  wrote results/demo/{name}")


def _engine() -> bool:
    from qflux.dynamic.solver import engine_available
    return engine_available()


def geojson(routes: list[dict], props=("vehicle", "time_min", "distance_km", "co2_kg")) -> dict:
    feats = [{"type": "Feature", "properties": {k: r.get(k) for k in props},
              "geometry": {"type": "LineString", "coordinates": [[p[1], p[0]] for p in r["geometry"]]}}
             for r in routes]
    return {"type": "FeatureCollection", "features": feats}


def nearest_area(latlon) -> str:
    return min(AREAS, key=lambda a: (AREAS[a][0] - latlon[0]) ** 2 + (AREAS[a][1] - latlon[1]) ** 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--time-s", type=float, default=5.0, help="planner time budget per solve")
    ap.add_argument("--S", type=float, default=None)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    metrics = {"generated_at": time.strftime("%Y-%m-%d %H:%M"), "scenario": "hyderabad-60",
               "weights": BALANCED, "planner_time_s": args.time_s}

    print("[1/4] Hyderabad-60 plans at 17:30 and 03:00")
    # QPSO: equal-evaluation budget (§11.3); time_s only bounds the OR-Tools stand-in
    from qflux.algos.registry import DEFAULT_ENGINE   # D59: QPSO-noQUBO (tuned), the shipped engine
    job = {"algorithm": DEFAULT_ENGINE, "weights": BALANCED, "seed": args.seed,
           "budget": {"evals": load_config()["budget"]["evals"], "time_s": None if _engine() else args.time_s},
           "job_id": "demo-1730"}
    r1730 = api.run_job(dict(HYD, tau0=1050), job)
    r0300 = api.run_job(dict(HYD, tau0=180), dict(job, job_id="demo-0300"))
    dump("result_demo.json", r1730); dump("result_0300.json", r0300)
    (OUT / "routes_1730.geojson").write_text(json.dumps(geojson(r1730["routes"])), encoding="utf-8")
    metrics["time_of_day"] = {"algorithm": r1730["algorithm"], "kpis_1730": r1730["kpis"], "kpis_0300": r0300["kpis"]}

    print("[2/4] Fleet impact: naive vs user_eq vs system_opt")
    t = time.time()
    fleet = api.fleet_compare(HYD, {"weights": BALANCED, "S": args.S, "seed": args.seed, "time_s": args.time_s})
    dump("fleet_demo.json", fleet)
    for m, r in fleet["modes"].items():
        (OUT / f"fleet_{m}.geojson").write_text(json.dumps(geojson(r["routes"])), encoding="utf-8")
    metrics["fleet"] = {"S": fleet["S"], "wall_s": round(time.time() - t, 1),
                        **{m: {k: r[k] for k in ("externality_veh_h", "max_vc", "edges_over_capacity",
                                                 "corridors_used")} | {"total_time_min": r["kpis"]["total_time_min"],
                                                                       "co2_kg": r["kpis"]["co2_kg"]}
                           for m, r in fleet["modes"].items()}}

    print("[3/4] Incident re-routing (zone on the busiest arterial used by the 17:30 plan)")
    inst = api.build_instance(HYD)
    b = bundle_for(inst)
    net = b.net
    from qflux.traffic.fleet_eq import flow_of
    routes = [r["stops"] for r in r1730["routes"]]
    f = flow_of(routes, b.paths[4], b.m, net.E)
    f[net.group != ARTERIAL] = 0
    # keep the zone away from the depot so it is a mid-route incident
    far = net.dist_km(net.edge_midpoints(), net.node_xy[b.terminals[0]]) > 3.0
    f[~far] = 0
    e = int(np.argmax(f))
    center = net.edge_midpoints()[e].round(6).tolist()
    incident = {"type": "zone", "center": center, "radius_m": 800, "factor": 2.5, "start_min": 1040,
                "end_min": 1160}
    t_inc = 1065.0
    inc_out = api.incident_reroute(HYD, {"incident": incident, "t_inc": t_inc, "weights": BALANCED,
                                         "routes": routes, "algorithm": r1730["algorithm"], "seed": args.seed})
    inc_out["incident_area"] = nearest_area(center)
    print("  warm vs cold re-optimisation")
    from qflux.dynamic.reroute import warm_vs_cold
    from qflux.traffic.route_eval import compute_refs
    inst_new = api.build_instance(dict(HYD, incidents=[incident]))
    wc = warm_vs_cold(inst_new, api.weights_from(BALANCED), compute_refs(inst, b), routes, time_s=args.time_s,
                      seed=args.seed)
    inc_out["warm_vs_cold"] = {k: {"algorithm": v["algorithm"], "time_budget_s": args.time_s / (3 if k == "warm" else 1),
                                   "convergence": v["convergence"]} for k, v in wc.items()}
    dump("incident_demo.json", inc_out)
    metrics["incident"] = dict(area=inc_out["incident_area"], **{k: inc_out["report"][k] for k in
                               ("accepted", "resequenced", "delay_increase_min", "delay_avoided_min", "reopt_time_s")})

    print("[4/4] Ambulance shortest path (Station A -> Hospital B, generic labels)")
    src = net.nearest_node(AREAS["Ameerpet"])
    dst = net.nearest_node(AREAS["Dilsukhnagar"])
    req = {"source": src, "target": dst, "depart_min": 1050, "algorithm": "dijkstra"}
    before = api.shortest_path(HYD, req)
    mid = before["halfway_by_time"]                 # path point at ~50% of the travel time (on the fastest path)
    sp_inc = {"type": "zone", "center": mid, "radius_m": 1000, "factor": 3, "start_min": 1050, "end_min": 1170}  # = live screen default
    after = api.shortest_path(HYD, dict(req, incidents=[sp_inc]))
    astar = api.shortest_path(HYD, dict(req, algorithm="astar", incidents=[sp_inc]))
    sp = {"source": net.node_xy[src].tolist(), "target": net.node_xy[dst].tolist(),
          "labels": {"source": "Station A (illustrative)", "target": "Hospital B (illustrative)"},
          "depart_min": 1050, "incident": sp_inc, "before": before, "after": after,
          "astar_check": {"eta_min": astar["eta_min"], "runtime_s": astar["runtime_s"],
                          "dijkstra_runtime_s": after["runtime_s"]},
          "explanation": [shortest_path_sentence(before, after)]}
    dump("shortest_path_demo.json", sp)
    metrics["ambulance"] = {"eta_before_min": before["eta_min"], "eta_after_min": after["eta_min"],
                            "astar_eta_min": astar["eta_min"], "dijkstra_s": after["runtime_s"],
                            "astar_s": astar["runtime_s"]}
    dump("metrics.json", metrics)


if __name__ == "__main__":
    main()
