"""Export real results into frontend/public/demo/ for offline demo mode (§8.3).

    python scripts/export_demo.py

Copies the artefacts written by scripts/run_fleet_demo.py and derives scenarios/home KPI files from them.
Benchmark and QUBO files are exported from results/tables/ when Person A's experiments exist; until then
the frontend keeps its clearly-labelled MOCK files for those screens.
"""
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

from qflux import api  # noqa: E402
from qflux.config import load_config  # noqa: E402

SRC = ROOT / "results" / "demo"
DST = ROOT / "frontend" / "public" / "demo"
TABLES = ROOT / "results" / "tables"
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
         "source": f"results/demo/metrics.json (S={f['S']:g}, simulated traffic, planner {tod['algorithm']})"},
        {"label": "Congestion delay at 17:30 vs 03:00 (same 60 customers)",
         "value": f"{tod['kpis_1730']['congestion_delay_min']:.0f} vs {tod['kpis_0300']['congestion_delay_min']:.0f}",
         "unit": "min", "source": "results/demo/result_demo.json, result_0300.json"},
        {"label": "Delay avoided by incident re-routing", "value": m["incident"]["delay_avoided_min"], "unit": "min",
         "source": "results/demo/incident_demo.json (simulated incident)"},
    ])

    # Person A's evidence, when present
    if (TABLES / "qubo_validation.csv").exists():
        write("qubo_validation.json", {"table": pd.read_csv(TABLES / "qubo_validation.csv").to_dict("records")})
    benches = sorted(TABLES.glob("bench_*.csv")) if TABLES.exists() else []
    if benches:
        write("benchmarks.json", [{"name": p.stem, "title": p.stem.replace("_", " ")} for p in benches])
        for p in benches:
            write(f"benchmark_{p.stem}.json", {"table": pd.read_csv(p).to_dict("records"), "figures": [],
                                              "meta": {"source": f"results/tables/{p.name}"}})
    else:
        print("  (no results/tables/bench_*.csv yet: benchmark/QUBO screens keep their MOCK files)")


if __name__ == "__main__":
    main()
