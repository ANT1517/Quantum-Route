"""D51 memory-pressure / throughput audit of timed (time-budget) runs.

    python scripts/audit_throughput.py [--exps bench_core_v1 bench_core_v1_noqubo ablation alpha_sweep scaling]

Per run, throughput proxies relative to the median of the same (experiment, budget, instance, algorithm):
  SA: moves/s;  hybrids (QPSO*, PSO+LS, GA+LS, RR+LS, cluster QPSO): evals/s and LS calls/s;
  every run with meta.cpu_calib_ops_s: calibration relative to the experiment median.
Flag: any proxy < 0.75 x median, or wall/budget > 1.02. OR-Tools has no work counter; it is checked on
wall/budget and calibration only.
Start times: meta.start_ts, else (bench_core_v1) results/logs/<exp>.arrivals.csv (start ~ arrival - wall_s).
Writes results/tables/d51_audit_runs.csv (all runs with ratios and flags) and d51_audit_summary.csv.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

THRESH, WALL = 0.75, 1.02
EXPS = ["bench_core_v1", "bench_core_v1_noqubo", "ablation", "alpha_sweep", "scaling"]


def arrivals(exp: str) -> dict[int, float]:
    p = ROOT / "results" / "logs" / f"{exp}.arrivals.csv"
    if not p.exists():
        return {}
    out = {}
    with open(p, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row.get("note"):
                out[int(row["line_index"])] = float(row["arrival_epoch_s"])
    return out


def load(exp: str, use_arrivals: bool = True) -> pd.DataFrame:
    rows, arr = [], (arrivals(exp) if use_arrivals else {})
    for i, line in enumerate(open(ROOT / "results" / "runs" / f"{exp}.jsonl", encoding="utf-8")):
        r = json.loads(line)
        if r["budget_type"] != "time":
            continue
        m = r.get("meta") or {}
        start = m.get("start_ts")
        if start is None and i in arr:
            start = arr[i] - r["wall_s"]
        work = m.get("moves") if r["algo"] == "sa" else r["evals_used"]
        rows.append({"exp": exp, "line": i, "algo": r["algo"], "instance": r["instance"], "budget": r["budget"],
                     "seed": r["seed"], "wall_s": r["wall_s"], "wall_ratio": r["wall_s"] / r["budget"],
                     "work_per_s": (work or 0) / r["wall_s"] if r["algo"] != "ortools" else np.nan,
                     "ls_per_s": (m.get("ls_calls") or 0) / r["wall_s"] if m.get("ls_calls") else np.nan,
                     "calib": m.get("cpu_calib_ops_s", np.nan), "start_ts": start})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exps", nargs="*", default=EXPS)
    ap.add_argument("--no-arrivals", action="store_true",
                    help="ignore <exp>.arrivals.csv (line indices no longer match after D51 moves)")
    ap.add_argument("--out", default="d51_audit", help="output prefix in results/tables")
    a = ap.parse_args()
    df = pd.concat([load(e, not a.no_arrivals) for e in a.exps], ignore_index=True)
    grp = ["exp", "budget", "instance", "algo"]
    for col in ("work_per_s", "ls_per_s"):
        df[col + "_rel"] = df[col] / df.groupby(grp)[col].transform("median")
    df["calib_rel"] = df["calib"] / df.groupby("exp")["calib"].transform("median")
    reasons = []
    for r in df.itertuples():
        why = []
        if r.work_per_s_rel < THRESH:
            why.append(f"{'moves' if r.algo == 'sa' else 'evals'}/s {r.work_per_s_rel:.2f}x")
        if r.ls_per_s_rel < THRESH:
            why.append(f"LS/s {r.ls_per_s_rel:.2f}x")
        if r.calib_rel < THRESH:
            why.append(f"calib {r.calib_rel:.2f}x")
        if r.wall_ratio > WALL:
            why.append(f"wall/budget {r.wall_ratio:.3f}")
        reasons.append("; ".join(why))
    df["flag_reason"] = reasons
    df["flagged"] = df.flag_reason != ""
    df["start_local"] = pd.to_datetime(df.start_ts, unit="s", utc=True).dt.tz_convert("Asia/Kolkata").dt.strftime("%H:%M")
    out = ROOT / "results" / "tables"
    df.to_csv(out / f"{a.out}_runs.csv", index=False, float_format="%.4g")
    summ = df.groupby("exp").agg(timed_runs=("line", "size"), flagged=("flagged", "sum"),
                                 min_work_rel=("work_per_s_rel", "min"), min_ls_rel=("ls_per_s_rel", "min"),
                                 min_calib_rel=("calib_rel", "min"), max_wall_ratio=("wall_ratio", "max"),
                                 runs_with_start_time=("start_ts", lambda s: int(s.notna().sum()))).reset_index()
    summ.to_csv(out / f"{a.out}_summary.csv", index=False, float_format="%.4g")
    pd.set_option("display.width", 220)
    print(summ.round(3).to_string(index=False))
    fl = df[df.flagged]
    print(f"\nflagged runs: {len(fl)}")
    if len(fl):
        print(fl[["exp", "algo", "instance", "budget", "seed", "start_local", "flag_reason"]].to_string(index=False))
        timed = df[df.start_ts.notna()].copy()
        timed["bin"] = pd.to_datetime(timed.start_ts, unit="s", utc=True).dt.tz_convert("Asia/Kolkata").dt.floor("10min").dt.strftime("%H:%M")
        print("\nflag rate by 10-minute start window:")
        print(timed.groupby("bin").agg(runs=("line", "size"), flagged=("flagged", "sum")).to_string())


if __name__ == "__main__":
    main()
