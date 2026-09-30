# Person A handoff (branch `Person-A`)

Written 2026-09-30 by Person B's Claude session, which started Person A's tasks while A was delayed.
**Everything here is yours to change.** Source of truth is still `QUANTUMROUTE_MASTER_DOC.md`.

## Branch layout
- `Person-A` was branched from `Person-B` (commit `6f1eee8`), not from `main`, so B's `qflux/api.py`,
  traffic code and Hyderabad data are available to your backend and tests. You only add A-owned folders,
  so merging later is trivial.
- Shared frozen files (`types.py`, `algos/base.py`, `configs/default.yaml`, `result.ts`,
  `tests/contract/`) are already in place. **Decision D24:** Hyderabad `Q = 200` (was 100, infeasible).
  D25–D27 are in doc §17.

## Setup
```
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt && pip install -e engine
python scripts/build_hyd.py          # ~45 s: rebuilds Hyderabad TD cache from committed data/hyd/roadnet.npz
pytest -q                            # contract + B's traffic/fleet tests + engine tests
```
Note: `pulp` must be **2.x** (`pulp>=2.8,<3`); PuLP 4.0 changed the `LpVariable` API. Python 3.13 works.

## Done (your task list)
| Task | Status | Files |
|---|---|---|
| 1. CVRPLIB A/P/CMT/X + `.sol` | done, 13 instances in `data/instances/` (downloaded from galgos.inf.puc-rio.br/cvrplib — old URLs 404) | |
| 1. `get_optimizer(name, params)` | done (real algorithms already, not only NN) | `algos/registry.py` |
| 1. TD fixture | done | `tests/fixtures/td_fixture.py` |
| 2. Loader (nint for A/P/X, exact for CMT, BKS) | done; recomputed cost of every BKS route = published BKS exactly | `bench/loader.py`, `core/distances.py` |
| 2. Encoding, Numba Split (static + TD), evaluator, NN refs, checker, LS | done | `core/*.py` |
| 2. QPSO | done with **all** §7.5 flags (P6 items too) | `algos/swarm.py`, `algos/qpso.py` |
| 3. PSO, GA, SA, +LS variants, OR-Tools wrapper, MILP, Held-Karp | code done | `algos/*.py` |
| 4. Tunneling, QUBO builder, backends (neal/brute/heldkarp/2opt/dwave stub), QUBO slot on gbest | code done | `algos/tunneling.py`, `quantum/*.py` |
| Tests T01–T07, T10, T28–T31 | written; 14 passed | `tests/engine/test_engine.py` |

## Not done — continue here
1. **Run `pytest tests/engine -q`** — T11 (MILP on P-n16-k8, PuLP 2.9) and the rest were interrupted, never confirmed.
2. **Benchmark harness** `bench/harness.py` (RunRecord JSONL, seed = seed_base + 1000·inst_idx + run_idx,
   config hash), `bench/stats.py` (Wilcoxon, Friedman), `bench/plots.py`, `scripts/run_bench.py --exp smoke`,
   `configs/experiments/*.yaml`. Tests T08–T09.
3. `scripts/run_qubo_check.py` → `results/tables/qubo_validation.csv` (neal vs brute vs 2-opt, A ∈ {1.5,3,6}×max d).
4. `algos/cluster.py` (sweep clustering for X-n502/X-n1001).
5. **Backend (P4)** — nothing written. `backend/app/...` per doc §4.3/§5.4/§5.6, calling `qflux.api`
   (`build_instance`, `run_job`, `shortest_path`, `fleet_compare`, `incident_reroute`, `scenario_detail`;
   `api.InfeasibleScenario` → 422, `sp.service.NoPath` → 404). Tests T18–T27.
   The frontend expects the WebSocket at **`/ws/jobs/{id}`** (root, not under `/api`) and sends job
   `params` as `{N, iterations, alpha_start, alpha_end}`; see `frontend/src/api/client.ts`.
6. Experiments (P9), then combine steps.

## Merge note for step 8
B's `engine/qflux/dynamic/solver.py` currently finds your optimizer by scanning `qflux.algos.<name>` for a
class with `.name == name`. Switch it to `from qflux.algos.registry import get_optimizer` when merging.

## Early measurements (single machine, NOT benchmark results — do not quote)
12,000 evals, 5 seeds, gap to BKS: A-n32-k5 — QPSO full 8.3%, QPSO w/o QUBO 7.9%, GA 7.3%, SA 3.0%,
OR-Tools 5 s ≈1.5% (1 seed). A-n63-k9 — QPSO full 11.3%, w/o QUBO 9.9%. So QPSO does not win yet (cf. Finding
F0). The QUBO slot (neal, 200 reads) costs ~0.13 s per route and made no improvements in these runs;
GA+LS scored worse than plain GA on mean (probably early convergence). Tuning limit: ≤ 4 configs on A-n44-k6 (D21).
