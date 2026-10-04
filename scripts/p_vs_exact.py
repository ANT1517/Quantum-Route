"""Heuristic vs exact on the small P instances (item 4): p_small runs next to the MILP table.

    python scripts/p_vs_exact.py
Per (instance, algorithm): runs, mean/max gap to the proven optimum (.sol, K = k), runs that reached it, median
time to reach it (first point of meta.curve_t at the optimum's F; runs that never reach it are excluded from the
median and counted). Writes results/tables/p_vs_exact.csv.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from qflux.bench.harness import read_records  # noqa: E402
from qflux.bench.loader import load_instance  # noqa: E402
from qflux.core.evaluate import Evaluator  # noqa: E402
from qflux.types import Weights  # noqa: E402


def main():
    recs = read_records(ROOT / "results" / "runs" / "p_small.jsonl")
    milp = pd.read_csv(ROOT / "results" / "tables" / "milp_p_instances.csv").set_index("instance")
    rows = []
    for inst_name in sorted({r["instance"] for r in recs}):
        inst = load_instance(inst_name)
        d_ref = Evaluator(inst, Weights(wT=0, wD=1)).refs.D
        opt_F = inst.bks / d_ref
        m = milp.loc[inst_name]
        rows.append({"instance": inst_name, "method": "MILP (CBC, 600 s)", "runs": 1, "budget_s": 600,
                     "mean_gap_pct": m.best_vs_optimum_pct, "max_gap_pct": m.best_vs_optimum_pct,
                     "reached_optimum": int(bool(m.cbc_result == "Optimal solution found")),
                     "median_time_to_optimum_s": m.wall_s if m.cbc_result == "Optimal solution found" else None,
                     "note": m.verdict})
        for algo in sorted({r["algo"] for r in recs}):
            rs = [r for r in recs if r["instance"] == inst_name and r["algo"] == algo]
            gaps = [r["gap_pct"] for r in rs if r["gap_pct"] is not None]
            times = []
            for r in rs:
                for t, f in (r["meta"].get("curve_t") or []):
                    if f <= opt_F * (1 + 1e-9) + 1e-12:
                        times.append(t)
                        break
            viol = sum(1 for r in rs if r["meta"].get("fleet_excess", 0) > 0)
            rows.append({"instance": inst_name, "method": algo, "runs": len(rs), "budget_s": rs[0]["budget"],
                         "mean_gap_pct": float(np.mean(gaps)) if gaps else None,
                         "max_gap_pct": float(np.max(gaps)) if gaps else None,
                         "reached_optimum": len(times),
                         "median_time_to_optimum_s": float(np.median(times)) if times else None,
                         "note": f"{viol} fleet violations" if viol else ""})
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "results" / "tables" / "p_vs_exact.csv", index=False, float_format="%.4g")
    pd.set_option("display.width", 200)
    print(df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
