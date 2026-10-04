"""Export the benchmark and QUBO data exactly as the backend serves them, for the frontend's demo mode.

    python scripts/export_api_json.py
Writes results/api_export/:
  benchmarks.json                 = GET /api/benchmarks
  benchmark_<name>.json           = GET /api/benchmarks/{name} for each listed benchmark
  qubo_validation.json            = GET /api/quantum/validation
  figures.txt                     = every figure path referenced (relative to results/, e.g. figures/x.png)
Demo mode resolves a figure "figures/x.png" to public/demo/figures/x.png, so copy those PNGs too
(Person B's scripts/export_demo.py; see MERGE_NOTES.md).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))

from backend.app.services import results_service as rs  # noqa: E402

OUT = ROOT / "results" / "api_export"


def write(name: str, obj) -> None:
    (OUT / name).write_text(json.dumps(obj, indent=1, allow_nan=False, default=str), encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    items = rs.list_benchmarks()
    write("benchmarks.json", items)
    figures = set()
    for it in items:
        b = rs.benchmark(it["name"])
        figures.update(b["figures"])
        write(f"benchmark_{it['name']}.json", b)
    write("qubo_validation.json", rs.qubo_validation())
    (OUT / "figures.txt").write_text("\n".join(sorted(figures)) + "\n", encoding="utf-8")
    print(f"exported {len(items)} benchmarks, qubo_validation, {len(figures)} figure paths -> {OUT}")


if __name__ == "__main__":
    main()
