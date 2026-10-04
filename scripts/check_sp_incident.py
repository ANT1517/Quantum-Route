"""D60 acceptance: the shortest-path "incident on the way" zone sits on the computed fastest path (at ~50% of its
travel time), so the ETA with the incident is >= the ETA before and usually differs.

    python scripts/check_sp_incident.py [--pairs 5] [--seed 2026]

Same requests as the Shortest Path screen (backend API, TestClient, temporary DB): random source/target points
inside the Hyderabad road network (seeded), departure 17:30, zone 1 km x3 for 120 min from departure, each pair on
a fresh copy of the Hyderabad-60 scenario. Writes results/tables/d60_sp_incident_check.csv.
"""
import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))
os.environ.setdefault("QR_DB_URL", f"sqlite:///{(Path(tempfile.mkdtemp()) / 'sp_check.db').as_posix()}")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import app  # noqa: E402
from qflux import api as engine  # noqa: E402

SPEC = {"source": "hyderabad", "n_customers": 60, "K": 6, "Q": 200, "seed": 7, "tau0": 1050}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=int, default=5)
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    net = engine.road_net(SPEC)
    rng = np.random.default_rng(a.seed)
    rows = []
    with TestClient(app) as c:
        for k in range(a.pairs):
            s, t = net.node_xy[rng.choice(len(net.node_xy), 2, replace=False)]
            sid = c.post("/api/scenarios", json={**SPEC, "name": f"sp-check-{k}"}).json()["scenario"]["id"]
            req = {"scenario_id": sid, "source": [float(s[0]), float(s[1])], "target": [float(t[0]), float(t[1])],
                   "depart_min": 1050, "algorithm": "dijkstra"}
            before = c.post("/api/shortest-path", json=req).json()
            center = before["halfway_by_time"]
            inc = {"type": "zone", "center": center, "radius_m": 1000, "factor": 3, "start_min": 1050, "end_min": 1170}
            affected = c.post(f"/api/scenarios/{sid}/incidents", json=inc).json()["affected_edges"]
            after = c.post("/api/shortest-path", json=req).json()
            rows.append({"pair": k, "source": req["source"], "target": req["target"], "zone_center": center,
                         "affected_edges": affected, "eta_before_min": before["eta_min"], "eta_after_min": after["eta_min"],
                         "delta_min": round(after["eta_min"] - before["eta_min"], 3),
                         "after_ge_before": after["eta_min"] >= before["eta_min"] - 1e-9,
                         "differs": abs(after["eta_min"] - before["eta_min"]) > 1e-6})
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "results" / "tables" / "d60_sp_incident_check.csv", index=False)
    pd.set_option("display.width", 200)
    print(df[["pair", "affected_edges", "eta_before_min", "eta_after_min", "delta_min", "after_ge_before", "differs"]].to_string(index=False))
    ok = df.after_ge_before.all() and df.differs.sum() >= max(1, a.pairs - 1)
    print(f"acceptance: after >= before in {int(df.after_ge_before.sum())}/{len(df)}; differs in {int(df.differs.sum())}/{len(df)} "
          f"-> {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
