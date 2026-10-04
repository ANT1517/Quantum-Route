"""Benchmark statistics (§11.5, §11.6): summary table, gap %, Wilcoxon signed-rank vs a reference
algorithm (paired by seed), Friedman test across instances.

Every table carries `runs`, `budget_type`, `budget` and `seeds` columns so its provenance travels with it.
Fleet rule (D38): a run whose final solution uses more than K vehicles counts as infeasible for gap purposes;
distance/gap statistics and the tests use only runs with m <= K, and `fleet_violations` counts the others.
"""
import numpy as np
import pandas as pd
from scipy import stats


def to_frame(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(records)


def fleet_ok(df: pd.DataFrame) -> pd.Series:
    """True for runs that respect the fleet limit (meta.fleet_excess == 0 or absent)."""
    if "meta" not in df:
        return pd.Series(True, index=df.index)
    return df["meta"].map(lambda m: not (isinstance(m, dict) and m.get("fleet_excess", 0) > 0))


def time_to_within(curve_t, final: float, frac: float) -> float | None:
    """First elapsed second at which best_F is within `frac` of this run's final best (wall-time curve)."""
    for t, f in curve_t or []:
        if f <= final * (1.0 + frac) + 1e-12:
            return float(t)
    return None


def evals_to_within(curve, final: float, frac: float = 0.05) -> int | None:
    """First evaluation count at which best_F is within `frac` of this run's final best (§11.5)."""
    for e, f in curve:
        if f <= final * (1.0 + frac) + 1e-12:
            return int(e)
    return None


def _seed_range(seeds) -> str:
    s = sorted(int(x) for x in seeds)
    return f"{s[0]}..{s[-1]}" if len(s) > 1 else str(s[0])


def summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    def med(xs):
        xs = [x for x in xs if x is not None]
        return float(np.median(xs)) if xs else None

    def sd(x):
        return float(x.std(ddof=1)) if len(x) > 1 else (0.0 if len(x) else None)

    for (bt, b, inst, algo), g_all in df.groupby(["budget_type", "budget", "instance", "algo"], sort=False):
        g = g_all[fleet_ok(g_all)]
        D = g["best_D"].to_numpy()
        gap = g["gap_pct"].dropna().astype(float).to_numpy()
        has_gap = len(gap) > 0
        ct = [m.get("curve_t") if isinstance(m, dict) else None for m in g.get("meta", [None] * len(g))]
        rows.append({
            "budget_type": bt, "budget": b, "instance": inst, "algo": algo, "runs": len(g_all),
            "runs_fleet_ok": len(g), "fleet_violations": len(g_all) - len(g),
            "seeds": _seed_range(g_all["seed"]),
            "F_mean": g["best_F"].mean() if len(g) else None, "F_std": sd(g["best_F"].to_numpy()),
            "D_best": D.min() if len(D) else None, "D_mean": D.mean() if len(D) else None,
            "D_median": float(np.median(D)) if len(D) else None, "D_worst": D.max() if len(D) else None,
            "D_std": sd(D),
            "gap_best_pct": gap.min() if has_gap else None,
            "gap_mean_pct": gap.mean() if has_gap else None,
            "gap_std_pct": sd(gap) if has_gap else None,
            "vehicles_mean": g_all["n_vehicles"].mean(),
            "evals_to_1pct_median": med(evals_to_within(c, f, 0.01) for c, f in zip(g["curve"], g["best_F"])),
            "evals_to_5pct_median": med(evals_to_within(c, f, 0.05) for c, f in zip(g["curve"], g["best_F"])),
            "time_to_1pct_s_median": med(time_to_within(c, f, 0.01) for c, f in zip(ct, g["best_F"])),
            "time_to_5pct_s_median": med(time_to_within(c, f, 0.05) for c, f in zip(ct, g["best_F"])),
            "evals_mean": g_all["evals_used"].mean(), "wall_s_mean": g_all["wall_s"].mean(),
            "ls_calls_mean": float(np.mean([m.get("ls_calls", 0) if isinstance(m, dict) else 0
                                            for m in g_all.get("meta", [{}] * len(g_all))])),
        })
    return pd.DataFrame(rows)


def wilcoxon_pair(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """(statistic, p) of the two-sided Wilcoxon signed-rank test; identical samples -> p = 1."""
    d = np.asarray(a, float) - np.asarray(b, float)
    if np.allclose(d, 0.0):
        return 0.0, 1.0
    res = stats.wilcoxon(a, b, zero_method="wilcox", alternative="two-sided")
    return float(res.statistic), float(res.pvalue)


def holm(pvals) -> np.ndarray:
    """Holm-Bonferroni adjusted p-values (step-down, monotone, capped at 1) for one family of tests."""
    p = np.asarray(pvals, float)
    m = len(p)
    if m == 0:
        return p
    order = np.argsort(p)
    adj = np.empty(m)
    running = 0.0
    for k, i in enumerate(order):
        running = max(running, min(1.0, (m - k) * p[i]))
        adj[i] = running
    return adj


def _effect(g: pd.DataFrame, a: str, b: str, seeds) -> tuple[float | None, float | None]:
    """(median, mean) paired difference in gap points, a - b, over the given seeds (None without gaps)."""
    gp = g.pivot_table(index="seed", columns="algo", values="gap_pct", aggfunc="first")
    if a not in gp or b not in gp:
        return None, None
    d = (gp.loc[gp.index.intersection(seeds), a] - gp.loc[gp.index.intersection(seeds), b]).dropna()
    return (float(d.median()), float(d.mean())) if len(d) else (None, None)


def _finish(rows: list[dict], alpha: float) -> pd.DataFrame:
    """Holm-Bonferroni across the whole table (one family per table)."""
    out = pd.DataFrame(rows)
    if len(out):
        out["p_holm"] = holm(out["p_value"].to_numpy())
        out["significant_holm"] = out["p_holm"] < alpha
        out["holm_family_size"] = len(out)
    return out


def wilcoxon_table(df: pd.DataFrame, reference: str, metric: str = "best_D", alpha: float = 0.05) -> pd.DataFrame:
    """Reference algorithm vs each other algorithm, paired by seed, per (budget, instance); fleet-feasible runs only.
    p_holm: Holm-Bonferroni over all comparisons in this table. Effect size: paired difference in gap points
    (reference - other; negative = reference better)."""
    df = df[fleet_ok(df)]
    rows = []
    for (bt, b, inst), g in df.groupby(["budget_type", "budget", "instance"], sort=False):
        piv = g.pivot_table(index="seed", columns="algo", values=metric, aggfunc="first")
        if reference not in piv:
            continue
        for algo in piv.columns:
            if algo == reference:
                continue
            pair = piv[[reference, algo]].dropna()
            if len(pair) < 2:
                continue
            stat, p = wilcoxon_pair(pair[reference].to_numpy(), pair[algo].to_numpy())
            diff = float(np.median(pair[reference] - pair[algo]))
            med_gap, mean_gap = _effect(g, reference, algo, pair.index)
            key = mean_gap if mean_gap is not None else float(np.mean(pair[reference] - pair[algo]))
            better = "ref better" if key < 0 else ("ref worse" if key > 0 else "tie")
            rows.append({"budget_type": bt, "budget": b, "instance": inst, "reference": reference,
                         "other": algo, "runs": len(pair), "seeds": _seed_range(pair.index),
                         "median_diff": diff, "median_diff_gap_pts": med_gap, "mean_diff_gap_pts": mean_gap,
                         "statistic": stat, "p_value": p, "significant": p < alpha, "direction": better})
    return _finish(rows, alpha)


def friedman_table(df: pd.DataFrame, metric: str = "best_D") -> pd.DataFrame:
    """Friedman test over instances (blocks) of mean `metric` per algorithm, plus average ranks; fleet-feasible runs."""
    df = df[fleet_ok(df)]
    rows = []
    for (bt, b), g in df.groupby(["budget_type", "budget"], sort=False):
        m = g.groupby(["instance", "algo"])[metric].mean().unstack("algo").dropna(axis=1)
        if m.shape[1] < 3 or m.shape[0] < 2:
            continue
        ranks = m.rank(axis=1).mean()
        stat, p = stats.friedmanchisquare(*[m[c].to_numpy() for c in m.columns])
        runs = int(g.groupby(["instance", "algo"]).size().min())
        for algo in m.columns:
            rows.append({"budget_type": bt, "budget": b, "algo": algo, "avg_rank": float(ranks[algo]),
                         "instances": m.shape[0], "runs_per_cell": runs,
                         "friedman_stat": float(stat), "p_value": float(p)})
    return pd.DataFrame(rows)


def chain_table(df: pd.DataFrame, chain: list[str], metric: str = "best_D", alpha: float = 0.05) -> pd.DataFrame:
    """Ablation: each row of `chain` vs the previous row, paired by seed (fleet-feasible runs only)."""
    df = df[fleet_ok(df)]
    rows = []
    for (bt, b, inst), g in df.groupby(["budget_type", "budget", "instance"], sort=False):
        piv = g.pivot_table(index="seed", columns="algo", values=metric, aggfunc="first")
        for prev, cur in zip(chain, chain[1:]):
            if prev not in piv or cur not in piv:
                continue
            pair = piv[[prev, cur]].dropna()
            if len(pair) < 2:
                continue
            stat, p = wilcoxon_pair(pair[cur].to_numpy(), pair[prev].to_numpy())
            diff = float(np.median(pair[cur] - pair[prev]))
            med_gap, mean_gap = _effect(g, cur, prev, pair.index)
            key = mean_gap if mean_gap is not None else float(np.mean(pair[cur] - pair[prev]))
            rows.append({"budget_type": bt, "budget": b, "instance": inst, "row": cur, "previous": prev,
                         "runs": len(pair), "seeds": _seed_range(pair.index),
                         "mean_row": float(pair[cur].mean()), "mean_previous": float(pair[prev].mean()),
                         "median_diff": diff, "median_diff_gap_pts": med_gap, "mean_diff_gap_pts": mean_gap,
                         "statistic": stat, "p_value": p, "significant": p < alpha,
                         "direction": "better" if key < 0 else ("worse" if key > 0 else "tie")})
    return _finish(rows, alpha)
