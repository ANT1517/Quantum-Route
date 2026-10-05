"""Tables the UI reads through GET /api/files are copied verbatim into the offline demo export
(scripts/export_demo.py, FILES_TABLES), so demo mode shows the same numbers as live mode."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TABLES = ["tables/milp_p_instances.csv"]


def _text(p: Path) -> str:
    return p.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_demo_files_tables_match_results():
    for rel in TABLES:
        assert _text(ROOT / "frontend" / "public" / "demo" / rel) == _text(ROOT / "results" / rel), rel
