"""Benchmark statistics (§11.5, §11.6): summary table, gap %, Wilcoxon signed-rank vs a reference
algorithm (paired by seed), Friedman test across instances.

Every table carries `runs`, `budget_type`, `budget` and `seeds` columns so its provenance travels with it.
"""
import numpy as np
import pandas as pd
from scipy import stats


def to_frame(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(records)


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
    for (bt, b, inst, algo), g in df.groupby(["budget_type", "budget", "instance", "algo"], sort=False):
        D = g["best_D"].to_numpy()
        gap = g["gap_pct"].astype(float).to_numpy() if g["gap_pct"].notna().all() else None
        e5 = [evals_to_within(c, f) for c, f in zip(g["curve"], g["best_F"])]
        e5 = [x for x in e5 if x is not None]
        rows.append({
            "budget_type": bt, "budget": b, "instance": inst, "algo": algo, "runs": len(g),
            "seeds": _seed_range(g["seed"]),
            "F_mean": g["best_F"].mean(), "F_std": g["best_F"].std(ddof=1) if len(g) > 1 else 0.0,
            "D_best": D.min(), "D_mean": D.mean(), "D_median": float(np.median(D)), "D_worst": D.max(),
            "D_std": D.std(ddof=1) if len(D) > 1 else 0.0,
            "gap_best_pct": None if gap is None else gap.min(),
            "gap_mean_pct": None if gap is None else gap.mean(),
            "vehicles_mean": g["n_vehicles"].mean(),
            "evals_to_5pct_median": float(np.median(e5)) if e5 else None,
            "evals_mean": g["evals_used"].mean(), "wall_s_mean": g["wall_s"].mean(),
        })
    return pd.DataFrame(rows)


def wilcoxon_pair(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """(statistic, p) of the two-sided Wilcoxon signed-rank test; identical samples -> p = 1."""
    d = np.asarray(a, float) - np.asarray(b, float)
    if np.allclose(d, 0.0):
        return 0.0, 1.0
    res = stats.wilcoxon(a, b, zero_method="wilcox", alternative="two-sided")
    return float(res.statistic), float(res.pvalue)


def wilcoxon_table(df: pd.DataFrame, reference: str, metric: str = "best_D", alpha: float = 0.05) -> pd.DataFrame:
    """Reference algorithm vs each other algorithm, paired by seed, per (budget, instance)."""
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
            better = "ref better" if diff < 0 else ("ref worse" if diff > 0 else "tie")
            rows.append({"budget_type": bt, "budget": b, "instance": inst, "reference": reference,
                         "other": algo, "runs": len(pair), "seeds": _seed_range(pair.index),
                         "median_diff": diff, "statistic": stat, "p_value": p,
                         "significant": p < alpha, "direction": better})
    return pd.DataFrame(rows)


def friedman_table(df: pd.DataFrame, metric: str = "best_D") -> pd.DataFrame:
    """Friedman test over instances (blocks) of mean `metric` per algorithm, plus average ranks."""
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
