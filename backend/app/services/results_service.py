"""Read-only access to results/ (§5.4 /benchmarks, /files, /quantum/validation). Numbers shown in the UI come
from these files only (§1.4). Tuning and smoke tables are listed with their kind so the UI never presents
them as benchmarks; superseded runs (bench_core_v0) have no tables and are never listed."""
import json
from pathlib import Path

import pandas as pd

from ..errors import ApiError
from ..settings import RESULTS_DIR

TABLES = RESULTS_DIR / "tables"
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


def list_benchmarks() -> list[dict]:
    out = []
    for p in sorted(TABLES.glob("*_summary.csv")):
        name = p.name[: -len("_summary.csv")]
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
    budgets = meta.get("budgets") or []
    out = {"table": _records(pd.read_csv(summ)),
           "figures": [f"figures/{p.name}" for p in sorted(FIGURES.glob(f"{name}_*.png"))],
           "meta": {**meta, "kind": kind_of(name), "runs": meta.get("runs_planned"),
                    "budget": ", ".join(f"{b['value']:g} {'s' if b['type'] == 'time' else 'evals'}" for b in budgets)}}
    for extra in ("wilcoxon", "friedman", "chain"):
        p = TABLES / f"{name}_{extra}.csv"
        if p.exists() and p.stat().st_size > 1:
            try:
                out[extra] = _records(pd.read_csv(p))
            except pd.errors.EmptyDataError:
                out[extra] = []
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
