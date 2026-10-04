"""Benchmark figures (§11.7): convergence (median + IQR of best F vs evaluations) and box plots of the gap.

Titles state runs, budget and seeds, so a figure is never shown without its provenance.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .stats import _seed_range, fleet_ok  # noqa: E402


def _on_grid(curve, grid):
    e = np.array([c[0] for c in curve], float)
    f = np.array([c[1] for c in curve], float)
    idx = np.searchsorted(e, grid, side="right") - 1
    out = np.where(idx >= 0, f[np.clip(idx, 0, None)], np.nan)
    return out


def convergence(df: pd.DataFrame, instance: str, budget: float, path: Path, exp: str = "") -> Path:
    g = df[(df.instance == instance) & (df.budget_type == "evals") & (df.budget == budget)]
    grid = np.arange(100, int(budget) + 1, 100)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for algo, ga in g.groupby("algo", sort=False):
        Y = np.vstack([_on_grid(c, grid) for c in ga["curve"]])
        med = np.nanmedian(Y, axis=0)
        q1, q3 = np.nanpercentile(Y, 25, axis=0), np.nanpercentile(Y, 75, axis=0)
        ax.plot(grid, med, label=algo, lw=1.6)
        ax.fill_between(grid, q1, q3, alpha=0.2)
    runs = int(g.groupby("algo").size().min())
    ax.set_xlabel("evaluations")
    ax.set_ylabel("best F (distance / nearest-neighbour distance)")
    ax.set_title(f"{instance}: median + IQR, {runs} runs, {int(budget)} evals, seeds {_seed_range(g.seed.unique())}",
                 fontsize=9)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def convergence_time(df: pd.DataFrame, instance: str, budget: float, path: Path, exp: str = "") -> Path:
    """Time-budget runs (D40): median + IQR of best F vs wall-clock seconds, from RunRecord.meta["curve_t"]."""
    g = df[(df.instance == instance) & (df.budget_type == "time") & (df.budget == budget)]
    g = g[fleet_ok(g)]
    grid = np.linspace(0.0, float(budget), 301)[1:]
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for algo, ga in g.groupby("algo", sort=False):
        curves = [m.get("curve_t") for m in ga["meta"] if isinstance(m, dict) and m.get("curve_t")]
        if not curves:
            continue
        Y = np.vstack([_on_grid(c, grid) for c in curves])
        with np.errstate(all="ignore"):
            med = np.nanmedian(Y, axis=0)
            q1, q3 = np.nanpercentile(Y, 25, axis=0), np.nanpercentile(Y, 75, axis=0)
        ax.plot(grid, med, label=algo, lw=1.6)
        ax.fill_between(grid, q1, q3, alpha=0.2)
    runs = int(g.groupby("algo").size().min()) if len(g) else 0
    ax.set_xlabel("wall-clock seconds (one core per run)")
    ax.set_ylabel("best F (distance / nearest-neighbour distance)")
    ax.set_title(f"{instance}: median + IQR, {runs} runs, {budget:g} s budget, seeds {_seed_range(g.seed.unique())}",
                 fontsize=9)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def gap_boxplot(df: pd.DataFrame, budget_type: str, budget: float, path: Path) -> Path | None:
    g = df[(df.budget_type == budget_type) & (df.budget == budget) & df.gap_pct.notna()]
    if g.empty:
        return None
    insts = list(dict.fromkeys(g.instance))
    algos = list(dict.fromkeys(g.algo))
    fig, axes = plt.subplots(1, len(insts), figsize=(3.2 * len(insts), 4.0), squeeze=False)
    for ax, inst in zip(axes[0], insts):
        gi = g[g.instance == inst]
        data = [gi[gi.algo == a].gap_pct.astype(float).to_numpy() for a in algos]
        ax.boxplot(data, tick_labels=algos)
        ax.set_title(inst, fontsize=9)
        ax.tick_params(axis="x", rotation=45, labelsize=8)
        ax.grid(alpha=0.3, axis="y")
    axes[0][0].set_ylabel("gap to BKS (%)")
    unit = "evals" if budget_type == "evals" else "s"
    runs = int(g.groupby(["instance", "algo"]).size().min())
    fig.suptitle(f"Final gap, {runs} runs, budget {budget:g} {unit}, seeds {_seed_range(g.seed.unique())}", fontsize=9)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def scaling_plot(df: pd.DataFrame, path: Path, rule: str | None = None) -> Path | None:
    """Gap to BKS and evaluations used vs n (log x), one line per algorithm; each point labelled with its budget."""
    import re
    g = df[fleet_ok(df)].copy()
    if g.empty:
        return None
    g["n"] = g.instance.map(lambda s: int(re.search(r"-n(\d+)", s).group(1)) - 1)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4))
    for algo, ga in g.groupby("algo", sort=False):
        s = ga.groupby(["n", "budget"]).agg(gap=("gap_pct", "median"), q1=("gap_pct", lambda x: x.quantile(0.25)),
                                            q3=("gap_pct", lambda x: x.quantile(0.75)),
                                            evals=("evals_used", "median")).reset_index().sort_values("n")
        a1.errorbar(s.n, s.gap, yerr=[s.gap - s.q1, s.q3 - s.gap], marker="o", capsize=3, label=algo)
        a2.plot(s.n, s.evals, marker="o", label=algo)
        for _, row in s.iterrows():
            a1.annotate(f"{row.budget:g} s", (row.n, row.gap), textcoords="offset points", xytext=(4, 4), fontsize=7)
    runs = int(g.groupby(["instance", "algo"]).size().min())
    for ax, lab in ((a1, "gap to BKS (%), median + IQR"), (a2, "evaluations used (median)")):
        ax.set_xscale("log")
        ax.set_xlabel("customers n (log scale)")
        ax.set_ylabel(lab)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    counts = g.groupby("instance").size().to_dict()
    fig.suptitle(f"Scaling: time budget {rule or 'per instance as labelled'}; runs per point: "
                 + ", ".join(f"{k} {int(v / g[g.instance == k].algo.nunique())}" for k, v in counts.items()),
                 fontsize=9)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
