"""MILP (PuLP/CBC, MTZ) on the small P instances vs their proven optima (§9 Phase 9 item 5, §7.9).

    python scripts/run_milp.py [--time-limit 600]

Writes results/tables/milp_p_instances.csv: CBC result line, best value found, CBC lower bound, gap %, wall
time, and the proven optimum from the .sol file. The table never claims an optimum CBC did not prove;
a run stopped by the limit is reported as "time limit, gap x%".
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

import pandas as pd  # noqa: E402

from qflux.algos.milp import solve_milp  # noqa: E402
from qflux.bench.harness import keep_awake  # noqa: E402
from qflux.bench.loader import fleet_size_from_name, load_instance  # noqa: E402
from qflux.core.evaluate import Evaluator  # noqa: E402
from qflux.core.feasibility import check  # noqa: E402
from qflux.types import Weights  # noqa: E402

INSTANCES = ["P-n16-k8", "P-n19-k2", "P-n22-k8"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--time-limit", type=float, default=None, help="seconds per instance (default: config milp)")
    a = ap.parse_args()
    keep_awake(True)
    rows = []
    for name in INSTANCES:
        inst = load_instance(name)
        inst.K = fleet_size_from_name(name)            # the proven optimum assumes k vehicles (D38)
        res = solve_milp(inst, a.time_limit, K=inst.K)
        ev = Evaluator(inst, Weights(wT=0, wD=1))
        feasible = check(inst, ev.solution_from_routes(res["routes"]))[0] if res["routes"] else None
        if res["optimal"]:
            verdict = "optimal (proved by CBC)"
        elif res["gap_pct"] is not None:
            verdict = f"time limit, gap {res['gap_pct']:.1f}%"
        else:
            verdict = res["cbc_result"] or res["status"]
        rows.append({"instance": name, "n": inst.n, "K": inst.K, "proven_optimum_sol": inst.bks,
                     "cbc_result": res["cbc_result"], "verdict": verdict, "best_value": res["objective"],
                     "lower_bound": res["bound"], "gap_pct": res["gap_pct"],
                     "best_vs_optimum_pct": None if res["objective"] is None
                     else 100.0 * (res["objective"] - inst.bks) / inst.bks,
                     "routes_feasible": feasible, "wall_s": res["wall_s"], "time_limit_s": res["time_limit_s"]})
        print(rows[-1])
    out = ROOT / "results" / "tables" / "milp_p_instances.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False, float_format="%.6g")
    print("wrote", out)
    keep_awake(False)


if __name__ == "__main__":
    main()
