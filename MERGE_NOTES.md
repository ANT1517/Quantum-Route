# Merge notes for Person B (from the `solver` branch)

Things on `solver` that touch shared files or affect B's code. Source of truth: `QUANTUMROUTE_MASTER_DOC.md` (v4.2, §17 D28–D38).

## Frozen shared files changed
- **`engine/qflux/types.py`: `RunRecord.meta: dict = field(default_factory=dict)`** (D37). Additive and backward compatible: a new last field with an empty default, so existing `RunRecord(...)` calls still work. `tests/contract/test_contract.py` now expects `"meta"` at the end of the `RunRecord` field list. Take `solver`'s version of both files on merge.
- **`QUANTUMROUTE_MASTER_DOC.md`** (v4.1 → v4.2): §5.1, §7.4, §7.5.3, §7.8, §8.2, §9 Phase 9, §9.4, §10.1 (T11), §11.1, §11.3, §11.4, §3.4, §17 (D28–D38). D24–D27 are B's; A's decisions start at D28.

## Frontend (B's code; not changed by A)
- **Benchmark Studio** (§8.2 wireframe, updated in the doc): the instance chips should be the core set **A-n32-k5, A-n63-k9, A-n80-k10, CMT1, CMT5, X-n101-k25** (no A-n44-k6, which is tuning-only), with **"Runs: 10"** and both budgets (12,000 evals / 30 s). Headline rows: QPSO-full, PSO+LS, GA+LS, SA, OR-Tools. Plain PSO/GA, QPSO-base and RR+LS belong to the ablation view.
- Table and figure names: `results/tables/bench_core_{summary,wilcoxon,friedman}.csv`, `bench_core_meta.json`, `results/figures/bench_core_convergence_<instance>.png`, `bench_core_gap_<budget>.png`. Every summary row carries `runs`, `budget_type`, `budget` and `seeds`.

## Engine behaviour B should know about
- **Fleet limit for CVRPLIB (D38):** `load_instance` now sets `K = k` (from the name) for Augerat A/P instances and `K = None` for CMT/X. `api.build_instance({"source": "cvrplib", ...})` inherits this; pass an explicit `K` in the spec if a screen needs something else.
- **Algorithm names:** `sa_ls` no longer exists (SA has no +LS variant). The new control `rr_ls` (D34) is ablation only.
- **`improve_routes(routes, ev, ops, max_rounds, deadline=None)`:** new optional `deadline` (epoch seconds). B's `dynamic/solver.py` call `improve_routes(..., max_rounds=1)` still works unchanged.
- **Time budgets (D31):** every optimizer now stops within ≈2% of `budget_s` (LS, QUBO slot, tunneling and final polish are deadline-aware). Demo timings may shift slightly.
- **QPSO now runs memetic LS (D33)**, so a 12,000-eval run takes longer than before (≈20 s on A-n44-k6 with 11 parallel workers). For the live demo, prefer a time budget.
- **Step 8 of the merge (unchanged):** switch `engine/qflux/dynamic/solver.py` to `from qflux.algos.registry import get_optimizer`, then re-run `run_fleet_demo.py` and `export_demo.py`.
- **Editable install:** the shared venv imports `qflux` from `~/Quantum-Route/engine` (B's worktree). After merging, reinstall (`pip install -e engine`) or set `PYTHONPATH=<repo>/engine`, otherwise tests import the wrong copy.
