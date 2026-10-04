"""Read-only access to results/ (§5.4 /benchmarks, /files, /quantum/validation). Numbers shown in the UI come
from these files only (§1.4). Tuning and smoke tables are listed with their kind so the UI never presents
them as benchmarks; superseded runs (bench_core_v0) have no tables and are never listed."""
import json
from pathlib import Path

import pandas as pd

from qflux.bench.harness import read_records

from ..errors import ApiError
from ..settings import RESULTS_DIR

TABLES = RESULTS_DIR / "tables"
RUNS = RESULTS_DIR / "runs"
FIGURES = RESULTS_DIR / "figures"
FILE_TYPES = {".png": "image/png", ".svg": "image/svg+xml", ".csv": "text/csv", ".json": "application/json",
              ".md": "text/markdown", ".geojson": "application/geo+json"}


def kind_of(name: str) -> str:
    if name.startswith("tune_"):
        return "tuning (not a benchmark)"
    if name.startswith("smoke"):
        return "smoke test (not a benchmark)"
    return "benchmark"


def _records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records"))


def list_benchmarks(include_all: bool = False) -> list[dict]:
    """Benchmark Studio has no kind filter, so tuning and smoke tables are hidden unless include_all."""
    out = []
    for p in sorted(TABLES.glob("*_summary.csv")):
        name = p.name[: -len("_summary.csv")]
        if not include_all and kind_of(name) != "benchmark":
            continue
        meta = _meta(name)
        out.append({"name": name, "title": meta.get("description") or name, "kind": kind_of(name),
                    "runs": meta.get("runs_planned"), "budgets": meta.get("budgets"), "records": meta.get("records")})
    return out


def _meta(name: str) -> dict:
    p = TABLES / f"{name}_meta.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def benchmark(name: str) -> dict:
    if "/" in name or "\\" in name or ".." in name:
        raise ApiError(404, "NOT_FOUND", f"benchmark {name} not found")
    summ = TABLES / f"{name}_summary.csv"
    if not summ.exists():
        raise ApiError(404, "NOT_FOUND", f"benchmark {name} not found")
    meta = _meta(name)
    summary = pd.read_csv(summ)
    refs = meta.get("references") or [meta.get("reference", "qpso")]
    for k, ref in enumerate(refs):
        wil = TABLES / (f"{name}_wilcoxon.csv" if k == 0 else f"{name}_wilcoxon_{ref}.csv")
        # Benchmark Studio's verdict reads the first column matching /wilcoxon/: the Holm-corrected p vs the
        # primary reference. Other columns avoid the word so they cannot be picked by mistake.
        pcol = f"wilcoxon_p_holm_vs_{ref}" if k == 0 else f"p_holm_vs_{ref}"
        for col in (pcol, f"p_raw_vs_{ref}", f"median_diff_gap_pts_vs_{ref}"):
            summary[col] = None
        if not wil.exists() or wil.stat().st_size <= 1:
            continue
        try:
            w = pd.read_csv(wil)
        except pd.errors.EmptyDataError:
            continue
        for _, r in w.iterrows():
            m = ((summary.instance == r.instance) & (summary.algo == r.other) &
                 (summary.budget_type == r.budget_type) & (summary.budget == r.budget))
            summary.loc[m, pcol] = r.get("p_holm", r.p_value)
            summary.loc[m, f"p_raw_vs_{ref}"] = r.p_value
            summary.loc[m, f"median_diff_gap_pts_vs_{ref}"] = r.get("median_diff_gap_pts")
    gaps = _gap_arrays(name, meta)                     # per-run gaps -> Benchmark Studio box plot
    summary["gap_runs_pct"] = [gaps.get((r.budget_type, float(r.budget), r.instance, r.algo), [])
                               for r in summary.itertuples()]
    out = {"table": _records(summary),
           "figures": [f"figures/{p.name}" for p in sorted(FIGURES.glob(f"{name}_*.png"))],
           "meta": {**meta, "kind": kind_of(name), "runs": meta.get("runs_planned"),
                    "budget": ", ".join(f"{b:g} {'s' if t == 'time' else 'evals'}"
                                        for t, b in sorted(set(zip(summary.budget_type, summary.budget))))}}
    for extra in ("wilcoxon", "friedman", "chain", *[f"wilcoxon_{r}" for r in refs[1:]]):
        p = TABLES / f"{name}_{extra}.csv"
        if p.exists() and p.stat().st_size > 1:
            try:
                out[extra] = _records(pd.read_csv(p))
            except pd.errors.EmptyDataError:
                out[extra] = []
    return out


def _gap_arrays(name: str, meta: dict) -> dict:
    """{(budget_type, budget, instance, algo): [gap % per fleet-feasible run]} from the run logs."""
    recs = read_records(RUNS / f"{name}.jsonl")
    for imp in meta.get("import_runs") or []:
        recs += [r for r in read_records(RUNS / f"{imp['exp']}.jsonl")
                 if r["instance"] in imp.get("instances", [r["instance"]])
                 and r["algo"] in imp.get("algorithms", [r["algo"]])]
    out: dict = {}
    for r in recs:
        if r.get("gap_pct") is None:
            continue
        out.setdefault((r["budget_type"], float(r["budget"]), r["instance"], r["algo"]), []).append(round(r["gap_pct"], 4))
    return out


def safe_file(path: str) -> tuple[Path, str]:
    """Whitelist: an existing file under results/, known type, no traversal (T26)."""
    if not path or ".." in Path(path).parts or path.startswith(("/", "\\")) or ":" in path:
        raise ApiError(404, "NOT_FOUND", "file not found")
    p = (RESULTS_DIR / path).resolve()
    root = RESULTS_DIR.resolve()
    if root not in p.parents or not p.is_file() or p.suffix.lower() not in FILE_TYPES:
        raise ApiError(404, "NOT_FOUND", "file not found")
    return p, FILE_TYPES[p.suffix.lower()]


def qubo_validation() -> dict:
    p = TABLES / "qubo_validation.csv"
    if not p.exists():
        raise ApiError(404, "NOT_AVAILABLE", "results/tables/qubo_validation.csv has not been produced yet "
                                             "(scripts/run_qubo_check.py)")
    return {"table": _records(pd.read_csv(p))}
