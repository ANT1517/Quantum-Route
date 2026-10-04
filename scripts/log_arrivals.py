"""Timestamp records as they are appended to a running experiment's JSONL (for runs started before
RunRecord.meta had start/end timestamps). Writes <exp>.arrivals.csv: line index, arrival epoch seconds.
A run's start time is then about arrival - wall_s (resolution: the poll interval).

    python scripts/log_arrivals.py bench_core_v1 [--poll 1.0]
Stops by itself when the experiment log reports "done in".
"""
import argparse
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exp")
    ap.add_argument("--poll", type=float, default=1.0)
    a = ap.parse_args()
    runs = ROOT / "results" / "runs" / f"{a.exp}.jsonl"
    log = ROOT / "results" / "logs" / f"{a.exp}.log"
    out = ROOT / "results" / "logs" / f"{a.exp}.arrivals.csv"
    seen = sum(1 for _ in open(runs, encoding="utf-8")) if runs.exists() else 0
    with open(out, "a", encoding="utf-8") as f:
        if out.stat().st_size == 0:
            f.write("line_index,arrival_epoch_s,note\n")
            f.write(f"{seen},{time.time():.3f},logger started; lines before this index have no arrival time\n")
        while True:
            n = sum(1 for _ in open(runs, encoding="utf-8")) if runs.exists() else 0
            now = time.time()
            for i in range(seen, n):
                f.write(f"{i},{now:.3f},\n")
            f.flush()
            seen = n
            if log.exists() and "done in" in log.read_text(encoding="utf-8", errors="replace"):
                break
            time.sleep(a.poll)


if __name__ == "__main__":
    main()
