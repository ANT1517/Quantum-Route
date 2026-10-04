"""Build results/SLIDE_NUMBERS.md: every number a slide or the README may quote, with its source file and row.
Numbers are read from results/ (never typed by hand, §1.4).

    python scripts/make_slide_numbers.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

import pandas as pd  # noqa: E402

T = ROOT / "results" / "tables"
rows: list[tuple[str, str, str, str]] = []      # id, statement, value, source


def add(id_, statement, value, source):
    rows.append((id_, statement, value, source))


def f(x, d=2):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "n/a"
    if d == 2 and 0 < abs(x) < 0.1:              # small values (e.g. 0.005 %) keep 3 decimals
        d = 3
    return f"{x:.{d}f}"


def main():
    meta = json.loads((T / "bench_core_v1_meta.json").read_text(encoding="utf-8"))
    s = pd.read_csv(T / "bench_core_v1_summary.csv")
    w1 = pd.read_csv(T / "bench_core_v1_wilcoxon.csv")
    w2 = pd.read_csv(T / "bench_core_v1_wilcoxon_qpso_noqubo.csv")
    fr = pd.read_csv(T / "bench_core_v1_friedman.csv")
    add("H0", "bench_core_v1: runs per (algorithm, instance); instances; budgets",
        f"{meta['runs_planned']} runs; {len(meta['instances'])} instances; 30 s (n<=80), 60 s (CMT5, X-n101)",
        "results/tables/bench_core_v1_meta.json")
    add("H1", "Fleet-limit violations across all bench_core_v1 runs", str(int(s.fleet_violations.sum())),
        "results/tables/bench_core_v1_summary.csv (fleet_violations)")
    add("H2", "Infeasible solutions in bench_core_v1", str(meta["infeasible"]), "results/tables/bench_core_v1_meta.json")
    for r in s.itertuples():
        add(f"G-{r.instance}-{r.algo}", f"Mean gap to BKS, {r.algo} on {r.instance} ({r.budget:g} s, {r.runs} runs)",
            f"{f(r.gap_mean_pct)} % (sd {f(r.gap_std_pct)})", f"results/tables/bench_core_v1_summary.csv ({r.instance}, {r.algo})")
    for tag, w in (("P", w1), ("PN", w2)):
        for r in w.itertuples():
            add(f"{tag}-{r.instance}-{r.other}", f"{r.reference} vs {r.other} on {r.instance}: Holm-corrected Wilcoxon p; "
                f"median paired gap difference ({r.reference} - {r.other})",
                f"p_holm {r.p_holm:.3g}; {f(r.median_diff_gap_pts, 3)} gap points",
                f"results/tables/bench_core_v1_wilcoxon{'' if tag == 'P' else '_qpso_noqubo'}.csv ({r.instance}, {r.other})")
    for r in fr.itertuples():
        add(f"F-{int(r.budget)}-{r.algo}", f"Friedman average rank, {r.algo}, {int(r.budget)} s ({r.instances} instances)",
            f"{r.avg_rank:.2f} (Friedman p {r.p_value:.3g})", "results/tables/bench_core_v1_friedman.csv")
    ch = pd.read_csv(T / "ablation_chain.csv")
    for r in ch.itertuples():
        add(f"A-{r.instance}-{r.row}", f"Ablation {r.row} vs {r.previous} on {r.instance} (30 s, {r.runs} paired runs)",
            f"mean gap change {f(r.mean_diff_gap_pts, 2)} points; p_holm {r.p_holm:.3g}",
            f"results/tables/ablation_chain.csv ({r.instance}, {r.row})")
    sc = pd.read_csv(T / "scaling_summary.csv")
    for r in sc.itertuples():
        add(f"S-{r.instance}-{r.algo}", f"Scaling: {r.algo} on {r.instance} ({r.budget:g} s, {r.runs} runs)",
            f"mean gap {f(r.gap_mean_pct)} %", f"results/tables/scaling_summary.csv ({r.instance}, {r.algo})")
    pe = T / "p_vs_exact.csv"
    if pe.exists():
        for r in pd.read_csv(pe).itertuples():
            add(f"E-{r.instance}-{r.method.split(' ')[0]}", f"{r.method} on {r.instance}: mean gap to proven optimum; runs at optimum",
                f"{f(r.mean_gap_pct)} %; {r.reached_optimum}/{r.runs}; median time to optimum {f(r.median_time_to_optimum_s, 3)} s",
                f"results/tables/p_vs_exact.csv ({r.instance}, {r.method})")
    qv = pd.read_csv(T / "qubo_validation.csv")
    for k, r in enumerate(qv.itertuples()):
        add(f"Q{k}", f"QUBO slot (neal, {r.num_reads} reads), {r.source}, A={r.A_factor_x_max_d} x max d: "
            "routes; optimal %; time per route neal / brute / 2-opt",
            f"{r.routes}; {f(r.neal_optimal_pct, 0)} %; {f(r.time_per_route_neal_ms, 0)} / {f(r.time_per_route_brute_ms, 1)} / "
            f"{f(r.time_per_route_2opt_ms, 2)} ms", "results/tables/qubo_validation.csv")
    d46 = T / "d46_td_ls_speed.csv"
    if d46.exists():
        d = pd.read_csv(d46)
        med = d.groupby("mode").ms.median()
        piv = d.pivot(index="tour", columns="mode", values="F_after")
        add("D46", "Hyderabad-60 LS call, generic vs proxy (median ms); TD cost ratio proxy/generic",
            f"{med['generic_td']:.1f} -> {med['proxy_td_verified']:.1f} ms; ratio {(piv.proxy_td_verified / piv.generic_td).mean():.4f}",
            "results/tables/d46_td_ls_speed.csv")
    cs = T / "confirm_d54_summary.csv"
    if cs.exists():
        for r in pd.read_csv(cs).itertuples():
            add(f"C-{r.instance}-{r.algo}", f"D54 confirmation (new seeds, same launch conditions): mean gap, {r.algo} on "
                f"{r.instance} ({r.budget:g} s, {r.runs} runs)", f"{f(r.gap_mean_pct)} % (sd {f(r.gap_std_pct)})",
                f"results/tables/confirm_d54_summary.csv ({r.instance}, {r.algo})")
        for r in pd.read_csv(T / "confirm_d54_wilcoxon.csv").itertuples():
            add(f"CP-{r.instance}-{r.other}", f"D54 confirmation: {r.reference} vs {r.other} on {r.instance}: Holm p; "
                "mean paired gap difference", f"p_holm {r.p_holm:.3g}; {f(r.mean_diff_gap_pts, 3)} gap points",
                f"results/tables/confirm_d54_wilcoxon.csv ({r.instance}, {r.other})")
    au = pd.read_csv(T / "d51_audit_final_summary.csv")
    add("D51", "Timed runs flagged by the final memory/throughput audit", str(int(au.flagged.sum())),
        "results/tables/d51_audit_final_summary.csv")
    out = ["# SLIDE_NUMBERS", "",
           "Every number used on a slide, in the README or in the pitch, with its source. Generated by "
           "`scripts/make_slide_numbers.py` from `results/tables/`; do not edit by hand.", "",
           "| ID | Statement | Value | Source |", "|---|---|---|---|"]
    out += [f"| {a} | {b} | {c} | `{d}` |" for a, b, c, d in rows]
    (ROOT / "results" / "SLIDE_NUMBERS.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote results/SLIDE_NUMBERS.md ({len(rows)} numbers)")


if __name__ == "__main__":
    main()
