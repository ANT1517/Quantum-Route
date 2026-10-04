# Merge notes for Person B (from the `solver` branch)

Things on `solver` that touch shared files or affect B's code. Source of truth: `QUANTUMROUTE_MASTER_DOC.md` (v4.4, §17 D28–D43).

## Frozen shared files changed
- **`engine/qflux/types.py`: `RunRecord.meta: dict = field(default_factory=dict)`** (D37). Additive and backward compatible: a new last field with an empty default, so existing `RunRecord(...)` calls still work. `tests/contract/test_contract.py` now expects `"meta"` at the end of the `RunRecord` field list. Take `solver`'s version of both files on merge.
- **`RunRecord.meta["curve_t"]`** (D40): list of `[elapsed_s, best_F]` at each improvement plus the final point, written for every algorithm. Additive (a key inside `meta`). Time-budget convergence charts in Benchmark Studio should use it, with wall-clock seconds on the x-axis.
- **`QUANTUMROUTE_MASTER_DOC.md`** (v4.1 → v4.4): §3.4, §5.1, §7.4, §7.5.3, §7.8, §8.2, §9 Phase 9, §9.4, §10.1 (T11), §11.1, §11.3, §11.4, §17 (D28–D43). D24–D27 are B's; A's decisions start at D28.

## Frontend (B's code; not changed by A)
- **Benchmark Studio** (§8.2 wireframe, updated in the doc): the instance chips should be the core set **A-n32-k5, A-n63-k9, A-n80-k10, CMT1, CMT5, X-n101-k25** (no A-n44-k6, which is tuning-only), with **"Runs: 30"** and time budgets only: **30 s** for A-n32, A-n63, A-n80, CMT1 and **60 s** for CMT5, X-n101 (D39, D40, D43). Convergence charts for bench_core use wall-clock seconds (`meta.curve_t`), not evaluations. Headline rows: QPSO-full, PSO+LS, GA+LS, SA, OR-Tools. Show `fleet_violations` next to the gap (runs with m > k have no gap, D38). Plain PSO/GA, QPSO-base and RR+LS belong to the ablation view.
- Table and figure names: `results/tables/bench_core_v1_{summary,wilcoxon,friedman}.csv`, `bench_core_v1_meta.json`, `results/figures/bench_core_v1_convergence_<instance>_time{30,60}.png`, `bench_core_v1_gap_time{30,60}.png`. Every summary row carries `runs`, `budget_type`, `budget` and `seeds`.

## Engine behaviour B should know about
- **Fleet limit for CVRPLIB (D38):** `load_instance` now sets `K = k` (from the name) for Augerat A/P instances and `K = None` for CMT/X. `api.build_instance({"source": "cvrplib", ...})` inherits this; pass an explicit `K` in the spec if a screen needs something else.
- **Algorithm names:** `sa_ls` no longer exists (SA has no +LS variant). The new control `rr_ls` (D34) is ablation only.
- **`improve_routes(routes, ev, ops, max_rounds, deadline=None)`:** new optional `deadline` (epoch seconds). B's `dynamic/solver.py` call `improve_routes(..., max_rounds=1)` still works unchanged.
- **Time budgets (D31):** every optimizer now stops within ≈2% of `budget_s` (LS, QUBO slot, tunneling and final polish are deadline-aware). Demo timings may shift slightly.
- **QPSO now runs memetic LS (D33)**; on static instances LS uses exact O(1)-delta kernels (D41, ≈100× faster, same results). Time-dependent instances (Hyderabad, SynthCity) still use the generic kernels. For the live demo, use a time budget.
- **bench_core v0 is superseded** (`results/runs/bench_core_v0_partial.*`): never show it.
- **Step 8 of the merge (unchanged):** switch `engine/qflux/dynamic/solver.py` to `from qflux.algos.registry import get_optimizer`, then re-run `run_fleet_demo.py` and `export_demo.py`.
- **Editable install:** the shared venv imports `qflux` from `~/Quantum-Route/engine` (B's worktree). After merging, reinstall (`pip install -e engine`) or set `PYTHONPATH=<repo>/engine`, otherwise tests import the wrong copy.
