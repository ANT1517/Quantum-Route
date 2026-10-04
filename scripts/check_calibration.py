"""D57 check: every run of an experiment must have a CPU calibration in the full-speed range.

    python scripts/check_calibration.py scaling_v2 [--min 3.0e6]
Prints min/median/max of meta.cpu_calib_ops_s and every run below --min; exit code 1 if any is below.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

RUNS = Path(__file__).resolve().parents[1] / "results" / "runs"

ap = argparse.ArgumentParser()
ap.add_argument("exp")
ap.add_argument("--min", type=float, default=3.0e6)
a = ap.parse_args()
recs = [json.loads(l) for l in open(RUNS / f"{a.exp}.jsonl", encoding="utf-8") if l.strip()]
cal = np.array([r["meta"].get("cpu_calib_ops_s", np.nan) for r in recs], float)
print(f"{a.exp}: {len(recs)} runs; calibration min {np.nanmin(cal):.3g}, median {np.nanmedian(cal):.3g}, "
      f"max {np.nanmax(cal):.3g} ops/s; missing {int(np.isnan(cal).sum())}")
low = [(r["instance"], r["algo"], r["seed"], c) for r, c in zip(recs, cal) if not c >= a.min]
for x in low:
    print("  below threshold:", x)
sys.exit(1 if low else 0)
