"""D51: move the runs flagged by scripts/audit_throughput.py out of each experiment's JSONL into
<exp>.d51_replaced.jsonl, so that re-running the experiment (resume) repeats exactly those runs with the
same seeds. Idempotent: a line already moved is not moved again.

    python scripts/d51_replace.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "results" / "runs"


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", default="d51_audit", help="audit prefix in results/tables (e.g. d51_audit_after)")
    a = ap.parse_args()
    audit = pd.read_csv(ROOT / "results" / "tables" / f"{a.audit}_runs.csv")
    flagged = audit[audit.flagged]
    if flagged.empty:
        print("nothing flagged")
        return
    for exp, g in flagged.groupby("exp"):
        path = RUNS / f"{exp}.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines()
        keys = {(r.algo, r.instance, float(r.budget), int(r.seed)) for r in g.itertuples()}
        keep, moved = [], []
        for line in lines:
            if not line.strip():
                continue
            r = json.loads(line)
            k = (r["algo"], r["instance"], float(r["budget"]), int(r["seed"]))
            (moved if k in keys and r["budget_type"] == "time" else keep).append(line)
        if len(moved) != len(keys):
            sys.exit(f"{exp}: expected {len(keys)} flagged records, found {len(moved)}")
        with open(RUNS / f"{exp}.d51_replaced.jsonl", "a", encoding="utf-8") as f:
            for line in moved:
                r = json.loads(line)
                r["d51_reason"] = g[(g.algo == r["algo"]) & (g.seed == r["seed"])].flag_reason.iloc[0]
                f.write(json.dumps(r) + "\n")
        path.write_text("\n".join(keep) + "\n", encoding="utf-8")
        print(f"{exp}: moved {len(moved)} flagged runs to {exp}.d51_replaced.jsonl ({len(keep)} kept)")


if __name__ == "__main__":
    main()
