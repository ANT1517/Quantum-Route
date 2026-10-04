#!/usr/bin/env bash
# Experiment queue after bench_core_v1 (§9 Phase 9). Waits for bench_core_v1 to finish, then runs everything in
# order and stops at the first failure. Logs: results/logs/<step>.log, progress: results/logs/queue.log.
#   bash scripts/run_queue.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-../Quantum-Route/.venv/Scripts/python.exe}"
export PYTHONPATH="$PWD/engine"
LOG=results/logs
mkdir -p "$LOG"
q() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG/queue.log"; }

q "waiting for bench_core_v1"
until grep -q "done in" "$LOG/bench_core_v1.log" 2>/dev/null; do sleep 20; done
q "bench_core_v1 finished; rebuilding its report with run provenance"
"$PY" scripts/run_bench.py --exp bench_core_v1 --report-only > "$LOG/bench_core_v1_report.log" 2>&1

q "cluster solver test"
"$PY" -m pytest -q -p no:cacheprovider tests/engine/test_bench.py -k cluster > "$LOG/test_cluster.log" 2>&1

q "profile QPSO-full on A-n80-k10 (30 s, idle machine)"
"$PY" scripts/profile_qpso.py --instance A-n80-k10 --time-s 30 > "$LOG/profile_qpso.log" 2>&1

for exp in bench_core_v1_noqubo ablation ablation_evals alpha_sweep scaling; do
  q "start $exp"
  "$PY" -u scripts/run_bench.py --exp "$exp" > "$LOG/$exp.log" 2>&1
  q "done $exp"
done

q "start MILP on P-n16/19/22 (600 s limit each)"
"$PY" -u scripts/run_milp.py --time-limit 600 > "$LOG/milp.log" 2>&1
q "queue finished"
