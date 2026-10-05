"""Export real results into frontend/public/demo/ for offline demo mode (§8.3).

    python scripts/export_demo.py

Copies the artefacts written by scripts/run_fleet_demo.py and derives scenarios/home KPI files from them.
Benchmark and QUBO files are copied from results/api_export/ (scripts/export_api_json.py), i.e. exactly what
the live API serves, plus the figures they reference. Tables the UI reads through GET /api/files (the MILP
table for Benchmarks > vs MILP) are copied byte-for-byte to the same relative path under public/demo/.

    python scripts/export_demo.py --tables-only   # only the /files tables (no other demo file is rewritten)
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

from qflux import api  # noqa: E402
from qflux.algos.registry import DISPLAY_NAMES  # noqa: E402
from qflux.config import load_config  # noqa: E402

SRC = ROOT / "results" / "demo"
DST = ROOT / "frontend" / "public" / "demo"
COPY = ["result_demo.json", "result_0300.json", "fleet_demo.json", "incident_demo.json", "shortest_path_demo.json"]


def write(name: str, obj) -> None:
    (DST / name).write_text(json.dumps(obj, indent=1), encoding="utf-8")
    print(f"  frontend/public/demo/{name}")


def main():
    missing = [f for f in COPY if not (SRC / f).exists()]
    if missing:
        sys.exit(f"missing {missing}: run `python scripts/run_fleet_demo.py` first")
    DST.mkdir(parents=True, exist_ok=True)
    for f in COPY:
        shutil.copyfile(SRC / f, DST / f)
        print(f"  frontend/public/demo/{f}")

    hyd = load_config()["hyd"]
    scen = {"id": "hyderabad-60", "name": "Hyderabad-60 (17:30)", "source": "hyderabad", "n_customers": 60,
            "K": hyd["K"], "Q": hyd["Q"], "seed": 7, "tau0": hyd["tau0"]}
    synth = {"id": "synth-60", "name": "SynthCity-60", "source": "synth", "n_customers": 60, "K": 6,
             "Q": 200, "seed": 0, "tau0": 1050}
    write("scenarios.json", [scen, synth])
    detail = api.scenario_detail({k: scen[k] for k in ("source", "n_customers", "K", "Q", "seed", "tau0")})
    detail["scenario"] = scen
    write("scenario_demo.json", detail)

    m = json.loads((SRC / "metrics.json").read_text(encoding="utf-8"))
    f = m["fleet"]
    ext_drop = 100 * (f["naive"]["externality_veh_h"] - f["system_opt"]["externality_veh_h"]) / f["naive"]["externality_veh_h"]
    tod = m["time_of_day"]
    write("home_kpis.json", [
        {"label": "Background delay cut by system-optimal routing", "value": round(ext_drop, 1), "unit": "%",
         "source": f"results/demo/metrics.json (S={f['S']:g}, simulated traffic, planner {DISPLAY_NAMES.get(tod['algorithm'], tod['algorithm'])})"},
        {"label": "Congestion delay at 17:30 vs 03:00 (same 60 customers)",
         "value": f"{tod['kpis_1730']['congestion_delay_min']:.0f} vs {tod['kpis_0300']['congestion_delay_min']:.0f}",
         "unit": "min", "source": "results/demo/result_demo.json, result_0300.json"},
        {"label": "Delay avoided by incident re-routing", "value": m["incident"]["delay_avoided_min"], "unit": "min",
         "source": "results/demo/incident_demo.json (simulated incident)"},
    ])

    # Benchmark Studio / Quantum Lab: copy the exact live-API JSON written by scripts/export_api_json.py, so
    # demo mode shows the same tables as live mode (headline first; tuning, audit and superseded tables are not
    # exported; Wilcoxon/Friedman tables travel inside their benchmark file instead of appearing as separate
    # "benchmarks"). Referenced figures are copied to public/demo/figures/.
    export = ROOT / "results" / "api_export"
    if not (export / "benchmarks.json").exists():
        sys.exit("missing results/api_export/: run `python scripts/export_api_json.py` first")
    items = json.loads((export / "benchmarks.json").read_text(encoding="utf-8"))
    wanted = {"benchmarks.json", "qubo_validation.json"} | {f"benchmark_{b['name']}.json" for b in items}
    for old in DST.glob("benchmark_*.json"):          # stale or MOCK benchmark files
        if old.name not in wanted:
            old.unlink()
            print(f"  removed stale frontend/public/demo/{old.name}")
    for name in sorted(wanted):
        shutil.copyfile(export / name, DST / name)
        print(f"  frontend/public/demo/{name}")
    figs = [ln.strip() for ln in (export / "figures.txt").read_text(encoding="utf-8").splitlines() if ln.strip()]
    for rel in figs:                                   # "figures/x.png" -> public/demo/figures/x.png
        src = ROOT / "results" / rel
        dst = DST / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    print(f"  frontend/public/demo/figures/ ({len(figs)} figures)")

    write("qubo_route_demo.json", qubo_route_demo())
    export_tables()


# Files the UI fetches through GET /api/files/<path> (path relative to results/). Demo mode resolves the same
# path to public/demo/<path>, so a verbatim copy keeps the offline screen identical to the live one.
FILES_TABLES = ["tables/milp_p_instances.csv"]


def export_tables() -> None:
    for rel in FILES_TABLES:
        dst = DST / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "results" / rel, dst)
        print(f"  frontend/public/demo/{rel}")


def qubo_route_demo() -> dict:
    """Quantum Lab demo: the route QUBO for one real route with <= 7 stops (neal, fixed seed) + brute-force optimum.
    Hyderabad-60 (K = 6) routes have about 10 stops; if none has <= 7, the stated short-route variant
    (K = 12, Q = 100, as in run_qubo_check) is planned with the shipped engine and its shortest route is used."""
    from qflux.algos.registry import DEFAULT_ENGINE
    from qflux.core.construct import dispatch_matrix
    from qflux.quantum.backends import MAX_STOPS, solve_route_request
    spec = {"source": "hyderabad", "n_customers": 60, "K": 6, "Q": 200, "seed": 7, "tau0": 1050}
    res = json.loads((SRC / "result_demo.json").read_text(encoding="utf-8"))
    label = "Hyderabad-60 (17:30), route of the demo plan"
    short = [r["stops"] for r in res["routes"] if 3 <= len(r["stops"]) <= MAX_STOPS]
    if not short:
        spec = dict(spec, K=12, Q=100)
        res = api.run_job(spec, {"algorithm": DEFAULT_ENGINE, "weights": {"wT": 0.5, "wD": 0.2, "wC": 0.2, "wE": 0.1},
                                 "seed": 7, "budget": {"time_s": 10}})
        short = [r["stops"] for r in res["routes"] if 3 <= len(r["stops"]) <= MAX_STOPS]
        label = "Hyderabad-60 short-route variant (K=12, Q=100, 17:30), planned with QPSO-noQUBO (tuned)"
    stops = sorted(short, key=len)[-1]                 # the longest route that still fits the QUBO slot
    inst = api.build_instance(spec)
    dist = dispatch_matrix(inst).tolist()
    out = solve_route_request({"route_stops": stops, "backend": "neal", "dist": dist, "seed": 7})
    out.update(route_stops=stops, backend="neal (classical simulated annealing, dwave-samplers)", label=label,
               distance="dispatch-slot travel time (minutes)")
    return out

if __name__ == "__main__":
    if "--tables-only" in sys.argv:
        export_tables()
    else:
        main()
