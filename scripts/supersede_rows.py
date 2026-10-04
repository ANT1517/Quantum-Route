"""Move all records of given algorithms out of an experiment's JSONL (kept in <exp>.<tag>_replaced.jsonl) so
that re-running the experiment (resume) repeats exactly those runs with the same seeds and budgets.

    python scripts/supersede_rows.py --exp bench_core_v1 --algos ortools --tag d55
"""
import argparse
import json
from pathlib import Path

RUNS = Path(__file__).resolve().parents[1] / "results" / "runs"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True)
    ap.add_argument("--algos", nargs="+", required=True)
    ap.add_argument("--tag", required=True)
    a = ap.parse_args()
    path = RUNS / f"{a.exp}.jsonl"
    keep, moved = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            (moved if json.loads(line)["algo"] in a.algos else keep).append(line)
    with open(RUNS / f"{a.exp}.{a.tag}_replaced.jsonl", "a", encoding="utf-8") as f:
        f.writelines(line + "\n" for line in moved)
    path.write_text("".join(line + "\n" for line in keep), encoding="utf-8")
    print(f"{a.exp}: moved {len(moved)} {a.algos} records to {a.exp}.{a.tag}_replaced.jsonl ({len(keep)} kept)")


if __name__ == "__main__":
    main()
