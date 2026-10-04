# Running experiments (rule D57: the standalone runner is the only way)

Every timed experiment runs through `scripts/runner.py`, started in **its own console window**. Never launch
`run_bench.py` (or any timed run) as a background job of an IDE, agent shell or terminal tab.

**Why:** on Windows, background-launched processes were throttled to about 2.3–2.5× less CPU than processes
in their own window (per-run CPU calibration: ≈1.45 M vs ≈3.5 M ops/s; D57). Mixing the two in one comparison
makes a time-budget benchmark unfair.

## Start
```powershell
$repo = "C:\path\to\Quantum-Route"; $py = "$repo\.venv\Scripts\python.exe"
Start-Process -FilePath $py -ArgumentList "scripts/runner.py --phase <phase>" -WorkingDirectory $repo -WindowStyle Minimized
```
Phases are listed in `PHASES` in `scripts/runner.py`; each is an ordered list of steps (benchmarks, audits).

What the runner does:
- **Lock:** refuses to start if another runner is alive (`results/run_info/runner.lock`).
- **Memory:** refuses to start with < 4 GB free. Before each step it waits for ≥ 2 GB; inside a benchmark the
  harness pauses new runs below 2 GB. Free memory is logged every minute to `results/run_info/mem_log.csv`.
- **Keep-awake:** asks Windows not to sleep for the runner's whole lifetime. Closing the lid can still suspend
  the laptop; a time-budget run longer than 1.10× its budget is then marked invalid and re-run on resume.
- **Logs:** progress in `results/logs/queue.log`, per-step logs in `results/logs/<step>.log`, status in
  `results/run_info/runner_status.json`. It stops at the first failing step.

## Stop
```powershell
powershell -NoProfile -File scripts/stop_runner.ps1
```
This kills the runner's whole process tree and verifies that no python or cbc process is left.

## After a run
1. `python scripts/audit_throughput.py --exps <exp> --no-arrivals --out d51_audit_<exp>` flags runs below
   0.75× the median throughput (D51). Re-run flagged runs with `scripts/d51_replace.py` and a runner phase.
2. `python scripts/check_calibration.py <exp>` checks that every run's 0.2 s CPU calibration is in the
   full-speed range.
3. `python scripts/run_bench.py --exp <exp> --report-only` rebuilds the tables and figures, then
   `python scripts/make_slide_numbers.py` and `python scripts/export_api_json.py` refresh the numbers and the
   demo-mode exports.

## Machine checklist
Plugged in, lid open, browsers and other heavy applications closed, nothing else running. Use the same power
plan for every run in one comparison (the plan is recorded in `<exp>.run_info.json`).
