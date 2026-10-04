#!/usr/bin/env bash
# Experiment queue after bench_core_v1 (order fixed on 2026-10-04): report refresh -> D45 noQUBO row ->
# ablation -> plain QPSO-base vs PSO (evals) -> α sweep -> scaling (D50) -> MILP -> D49 P-core check ->
# QPSO profile -> run_qubo_check -> backend job tests. Stops at the first failure.
# Logs: results/logs/<step>.log; progress: results/logs/queue.log.   bash scripts/run_queue2.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-../Quantum-Route/.venv/Scripts/python.exe}"
export PYTHONPATH="$PWD/engine"
LOG=results/logs
mkdir -p "$LOG"
q() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG/queue.log"; }
others() {   # other python processes of this repo still running (e.g. a leftover report)
  powershell -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -like '*run_bench.py*' }).Count"
}

q "queue2: waiting for leftover run_bench processes to exit"
while [ "$(others | tr -d '\r')" != "0" ] && [ -n "$(others | tr -d '\r')" ]; do sleep 10; done

step() { local name="$1"; shift; q "start $name"; "$@" > "$LOG/$name.log" 2>&1; q "done $name"; }

step bench_core_v1_report      "$PY" scripts/run_bench.py --exp bench_core_v1 --report-only
step bench_core_v1_noqubo      "$PY" -u scripts/run_bench.py --exp bench_core_v1_noqubo
step bench_core_v1_report2     "$PY" scripts/run_bench.py --exp bench_core_v1 --report-only   # adds the D45 row
step ablation                  "$PY" -u scripts/run_bench.py --exp ablation
step ablation_evals            "$PY" -u scripts/run_bench.py --exp ablation_evals
step alpha_sweep               "$PY" -u scripts/run_bench.py --exp alpha_sweep
step test_cluster              "$PY" -m pytest -q -p no:cacheprovider tests/engine/test_bench.py -k cluster
step scaling                   "$PY" -u scripts/run_bench.py --exp scaling
step milp                      "$PY" -u scripts/run_milp.py --time-limit 600
step pcore_check               "$PY" -u scripts/run_bench.py --exp pcore_check
step profile_qpso              "$PY" scripts/profile_qpso.py --instance A-n80-k10 --time-s 30
step qubo_check                "$PY" -u scripts/run_qubo_check.py
step api_job_tests             "$PY" -m pytest -q -p no:cacheprovider tests/api
q "queue2 finished"
