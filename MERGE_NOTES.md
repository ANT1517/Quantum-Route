# Merge notes for Person B (from the `solver` branch)

Things on `solver` that touch shared files or affect B's code. Source of truth: `QUANTUMROUTE_MASTER_DOC.md` (v4.7, §17 D28–D52).

## Frozen shared files changed
- **`engine/qflux/types.py`: `RunRecord.meta: dict = field(default_factory=dict)`** (D37). Additive and backward compatible: a new last field with an empty default, so existing `RunRecord(...)` calls still work. `tests/contract/test_contract.py` now expects `"meta"` at the end of the `RunRecord` field list. Take `solver`'s version of both files on merge.
- **`RunRecord.meta["curve_t"]`** (D40): list of `[elapsed_s, best_F]` at each improvement plus the final point, written for every algorithm. Additive (a key inside `meta`). Time-budget convergence charts in Benchmark Studio should use it, with wall-clock seconds on the x-axis.
- **`QUANTUMROUTE_MASTER_DOC.md`** (v4.1 → v4.7): §3.4, §5.1, §7.4, §7.5.3, §7.8, §8.2, §9 Phase 9, §9.4, §10.1 (T11), §11.1, §11.3, §11.4, §17 (D28–D52). D24–D27 are B's; A's decisions start at D28.

## Frontend (B's code; not changed by A)
- **Benchmark Studio** (§8.2 wireframe, updated in the doc): the instance chips should be the core set **A-n32-k5, A-n63-k9, A-n80-k10, CMT1, CMT5, X-n101-k25** (no A-n44-k6, which is tuning-only), with **"Runs: 30"** and time budgets only: **30 s** for A-n32, A-n63, A-n80, CMT1 and **60 s** for CMT5, X-n101 (D39, D40, D43). Convergence charts for bench_core use wall-clock seconds (`meta.curve_t`), not evaluations. Headline rows: QPSO-full, PSO+LS, GA+LS, SA, OR-Tools. Show `fleet_violations` next to the gap (runs with m > k have no gap, D38). Plain PSO/GA, QPSO-base and RR+LS belong to the ablation view.
- Table and figure names: `results/tables/bench_core_v1_{summary,wilcoxon,friedman}.csv`, `bench_core_v1_meta.json`, `results/figures/bench_core_v1_convergence_<instance>_time{30,60}.png`, `bench_core_v1_gap_time{30,60}.png`. Every summary row carries `runs`, `budget_type`, `budget` and `seeds`.

## Backend (P4, A's code): what the frontend talks to
- Run from the repo root: `uvicorn backend.app.main:app --port 8000` (deps: `backend/requirements.txt`; SQLAlchemy 2 and websockets were added to the venv). REST under `/api`, WebSocket at **`/ws/jobs/{id}`** (root, as `client.ts` expects). OpenAPI at `/docs`.
- Seeded scenarios: **Hyderabad-60** and **SynthCity-60**. Errors always `{"error": {code, message}}`: shape errors 400 `INVALID_INPUT` (field list in the message), infeasible scenario 422 `INFEASIBLE`, weights not summing to 1 → 422 `WEIGHTS`, 3rd concurrent job → 429 `TOO_MANY_JOBS`, result before finish → 409 `NOT_FINISHED`.
- Job `params` `{N, iterations, alpha_start, alpha_end}` are translated (D48): α start/end → linear schedule; `iterations` → N×iterations evaluations if no budget is given; no budget → 10 s; time budgets capped at the 120 s job timeout (timeout → `COMPLETED_PARTIAL`). Optional header `Idempotency-Key` on POST /jobs. `algorithm: "milp"` → 422 (not a platform job).
- WebSocket events: `{type: "progress", iter, evals, best_F, progress}` every 5 iterations, then `{type: "completed"|"failed", status}` and close; unknown job → close code 4404.
- `/quantum/solve-route`: `route_stops` are customer ids (1..60) of Hyderabad-60; distances = its dispatch-slot travel times. `/quantum/validation` returns 404 `NOT_AVAILABLE` until `results/tables/qubo_validation.csv` exists.
- `/benchmarks` items carry `kind` (`benchmark` / `tuning (not a benchmark)` / `smoke test (not a benchmark)`); show only `benchmark` items in Benchmark Studio. `/benchmarks/{name}` adds `wilcoxon`, `friedman` and (ablation) `chain` tables.
- `qflux/api.py` (B's) is called unchanged. `run_job` still returns the demo JSON for `source: "cvrplib"`.
- Tests: `tests/api/test_api.py`; the `jobs`-marked tests run real optimizations (`pytest -m "not jobs"` for a quick pass).

## Frontend fit check (2026-10-04; B's files read only, nothing edited)
Fixed on A's side:
- `GET /benchmarks` now lists **benchmarks only** (Benchmark Studio has no kind filter); `?all=true` adds tuning/smoke tables.
- `GET /benchmarks/{name}` rows now carry `wilcoxon_p_vs_<reference>` (what `lib/verdict.ts` looks for with `/wilcoxon/`; it is the p-value of that row's algorithm vs QPSO-full, null on the QPSO row) and `gap_runs_pct` (per-run gaps, so the box plot renders). `meta.runs` and `meta.budget` (e.g. "30 s, 60 s") are set. Column names the verdict uses: `instance`, `algo`, `gap_mean_pct` (percent).
- `POST /quantum/solve-route` accepts optional `job_id` / `scenario_id`; without them the backend finds the job whose result contains exactly that route (Quantum Lab sends a route of the last job) and falls back to Hyderabad-60. The response adds `scenario_id`, `scenario_name`.
Needs B:
- **`scripts/export_demo.py`** globs `results/tables/bench_*.csv`, so it would export `bench_core_v1_summary`, `_wilcoxon` and `_friedman` as three separate "benchmarks", with `figures: []` and no `runs`/`budget` in meta. Suggested: export only benchmarks from `GET /benchmarks` (or `backend.app.services.results_service.list_benchmarks()`), and write each file as `results_service.benchmark(name)` returns it (same shape as live mode, figures included, copying the PNGs into `public/demo/figures/`). Also export `qubo_validation.json` from `results/tables/qubo_validation.csv` (already handled).
- Optional: send `job_id` in solve-route requests from Quantum Lab.
- Convergence overlay (S8) plots best F vs evaluations of platform jobs; benchmark convergence figures for bench_core are wall-clock (time budgets, D40).

## Engine behaviour B should know about
- **Fleet limit for CVRPLIB (D38):** `load_instance` now sets `K = k` (from the name) for Augerat A/P instances and `K = None` for CMT/X. `api.build_instance({"source": "cvrplib", ...})` inherits this; pass an explicit `K` in the spec if a screen needs something else.
- **Algorithm names:** `sa_ls` no longer exists (SA has no +LS variant). The new control `rr_ls` (D34) is ablation only.
- **`improve_routes(routes, ev, ops, max_rounds, deadline=None)`:** new optional `deadline` (epoch seconds). B's `dynamic/solver.py` call `improve_routes(..., max_rounds=1)` still works unchanged.
- **Time budgets (D31):** every optimizer now stops within ≈2% of `budget_s` (LS, QUBO slot, tunneling and final polish are deadline-aware). Demo timings may shift slightly.
- **Time-dependent LS (D46):** Hyderabad/SynthCity now use static-proxy LS with TD verification by default (≈42× faster per LS call on Hyderabad-60, never worse than its input, not identical to the old kernel). `improve_routes(..., td_proxy=False)` restores the old behaviour if a demo must reproduce earlier numbers exactly. Re-run `run_fleet_demo.py` / `export_demo.py` after the merge anyway (step 8).
- **Backend job timeout (D52):** a job's time budget is capped at the 120 s timeout and enforced inside the optimizer; T25 runs at n = 399.
- **QPSO now runs memetic LS (D33)**; on static instances LS uses exact O(1)-delta kernels (D41, ≈100× faster, same results). Time-dependent instances (Hyderabad, SynthCity) still use the generic kernels. For the live demo, use a time budget.
- **bench_core v0 is superseded** (`results/runs/bench_core_v0_partial.*`): never show it.
- **Step 8 of the merge (unchanged):** switch `engine/qflux/dynamic/solver.py` to `from qflux.algos.registry import get_optimizer`, then re-run `run_fleet_demo.py` and `export_demo.py`.
- **Editable install:** the shared venv imports `qflux` from `~/Quantum-Route/engine` (B's worktree). After merging, reinstall (`pip install -e engine`) or set `PYTHONPATH=<repo>/engine`, otherwise tests import the wrong copy.
