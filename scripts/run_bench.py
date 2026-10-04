"""Run a benchmark experiment and write its tables and figures (§9 Phase 2, §11).

    python scripts/run_bench.py --exp smoke            # configs/experiments/smoke.yaml
    python scripts/run_bench.py --exp bench_core --runs 10
    python scripts/run_bench.py --exp smoke --report-only

Outputs:
    results/runs/<exp>.jsonl                 one RunRecord per line (resumable)
    results/runs/<exp>.infeasible.jsonl      only if the checker rejected a solution
    results/tables/<exp>_summary.csv         best/mean/std/median/worst, gap %, evals to 5 %, time
    results/tables/<exp>_wilcoxon.csv        reference algorithm vs each baseline, paired by seed
    results/tables/<exp>_friedman.csv        average ranks across instances
    results/tables/<exp>_meta.json           runs, budgets, seeds, infeasible count, config hashes
    results/figures/<exp>_convergence_<instance>.png, <exp>_gap_<budget>.png
Runs use up to (physical cores - 1) single-threaded processes (D30); do not run two experiments at once.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

import pandas as pd  # noqa: E402

from qflux.bench import plots, stats  # noqa: E402
from qflux.bench.harness import keep_awake, load_experiment, read_records, run_experiment  # noqa: E402

TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "results" / "figures"
RUNS = ROOT / "results" / "runs"


def report(exp: dict, runs_dir: Path = RUNS, tables: Path = TABLES, figures: Path = FIGURES) -> dict:
    name = exp["name"]
    recs = read_records(runs_dir / f"{name}.jsonl")
    bad = read_records(runs_dir / f"{name}.infeasible.jsonl")
    if not recs:
        raise SystemExit(f"no records in {runs_dir / f'{name}.jsonl'}")
    df = stats.to_frame(recs)
    tables.mkdir(parents=True, exist_ok=True)
    out = {"summary": tables / f"{name}_summary.csv", "wilcoxon": tables / f"{name}_wilcoxon.csv",
           "friedman": tables / f"{name}_friedman.csv", "meta": tables / f"{name}_meta.json", "figures": []}
    stats.summary(df).to_csv(out["summary"], index=False, float_format="%.6g")
    ref = exp.get("reference", "qpso")
    stats.wilcoxon_table(df, ref).to_csv(out["wilcoxon"], index=False, float_format="%.6g")
    stats.friedman_table(df).to_csv(out["friedman"], index=False, float_format="%.6g")
    if exp.get("scaling_figure") or name.startswith("scaling"):
        p = plots.scaling_plot(df, figures / f"{name}_gap_vs_n.png")
        if p:
            out["figures"].append(p)
    if exp.get("chain"):                              # ablation: each row vs the previous row
        out["chain"] = tables / f"{name}_chain.csv"
        stats.chain_table(df, exp["chain"]).to_csv(out["chain"], index=False, float_format="%.6g")
    for (bt, b), g in df.groupby(["budget_type", "budget"], sort=False):
        for inst in dict.fromkeys(g.instance):
            fig = figures / f"{name}_convergence_{inst}_{bt}{b:g}.png"
            if bt == "evals":
                out["figures"].append(plots.convergence(df, inst, b, fig, name))
            else:                                   # time budgets: wall-clock x-axis (D40)
                out["figures"].append(plots.convergence_time(df, inst, b, fig, name))
        p = plots.gap_boxplot(df, bt, b, figures / f"{name}_gap_{bt}{b:g}.png")
        if p:
            out["figures"].append(p)
    meta = {
        "experiment": name, "description": exp.get("description", ""), "reference": ref,
        "weights": exp.get("weights", [0, 1, 0, 0]), "runs_planned": int(exp.get("runs", 3)),
        "records": len(recs), "infeasible": len(bad),
        "budgets": [{"type": b["type"], "value": b["value"], "algorithms": b["algorithms"]} for b in exp["budgets"]],
        "instances": exp["instances"],
        "seeds": sorted({int(r["seed"]) for r in recs}),
        "config_hashes": {f"{a}|{bt}|{b:g}": sorted(g.config_hash.unique().tolist())
                          for (a, bt, b), g in df.groupby(["algo", "budget_type", "budget"])},
        "note": "Measured on one machine; wall times depend on hardware.",
        "launches": json.loads((runs_dir / f"{name}.run_info.json").read_text(encoding="utf-8"))
        if (runs_dir / f"{name}.run_info.json").exists() else None,
    }
    out["meta"].write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True, help="experiment name in configs/experiments or a yaml path")
    ap.add_argument("--runs", type=int, help="override the number of runs per (algorithm, instance)")
    ap.add_argument("--report-only", action="store_true", help="only rebuild tables and figures")
    ap.add_argument("--workers", type=int, help="parallel processes (default: physical cores - 1, D30)")
    a = ap.parse_args()
    exp = load_experiment(a.exp)
    if a.runs:
        exp["runs"] = a.runs
    if not a.report_only:
        keep_awake(True)
        try:
            run_experiment(exp, workers=a.workers)
        finally:
            keep_awake(False)
    out = report(exp)
    pd.set_option("display.width", 200)
    print(pd.read_csv(out["summary"])[["budget_type", "budget", "instance", "algo", "runs", "D_mean", "gap_mean_pct",
                                         "gap_best_pct", "wall_s_mean"]].to_string(index=False))
    print("\nwrote:", *[str(p) for k, p in out.items() if k != "figures"], *map(str, out["figures"]), sep="\n  ")


if __name__ == "__main__":
    main()
