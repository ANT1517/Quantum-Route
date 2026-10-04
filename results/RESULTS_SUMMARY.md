# QuantumRoute: results summary (2026-10-04)

All numbers come from `results/tables/`; every quotable number has an ID in `results/SLIDE_NUMBERS.md`.
Gaps are % above the best-known solution. "Significant" means Holm–Bonferroni-corrected Wilcoxon p < 0.05 within that table.
**Engine shipped in the app = engine benchmarked below:** QPSO-noQUBO (tuned), i.e. QUBO slot off, fixed α = 0.3 (D59).

## Headline (D58): equal conditions, new seeds, 30 runs per algorithm and instance
Source: `confirm_d54` (all algorithms launched the same way, seeds 65345–71374, Holm correction over 18 comparisons, 0 infeasible, 0 fleet violations).

**Under equal conditions, QPSO-noQUBO (tuned):**
- **significantly beats tuned PSO+LS** on A-n63-k9, A-n80-k10, CMT5 and X-n101-k25 (mean paired difference −0.33, −2.11, −1.72 and −0.28 gap points) *(CP-<instance>-pso_tuned)*;
- **significantly beats Google OR-Tools** on A-n63-k9 (0.94% vs 1.55%), A-n80-k10 (1.18% vs 1.71%) and X-n101-k25 (1.83% vs 5.59%);
- **ties OR-Tools** (no significant difference) on A-n32-k5 and CMT5;
- **is behind OR-Tools** on CMT1 (0.26% vs 0.00%) *(C-<instance>-<algo>, CP-<instance>-ortools)*.

On A-n32-k5 and CMT1, tuned PSO+LS has the lower mean (0.00% vs 1.28%; 0.05% vs 0.26%), but the difference is not significant (Holm p = 0.056 and 0.080).

**Earlier results that still stand:**
- **v1 wins over the other metaheuristics** (bench_core_v1, QPSO-noQUBO with adaptive α; all rows under equal throttling). QPSO-noQUBO significantly beats:
  - GA+LS on A-n32-k5, A-n63-k9, A-n80-k10 and CMT1;
  - SA on all six core instances;
  - random-restart+LS on A-n63-k9, A-n80-k10, CMT1, CMT5 and X-n101-k25 *(PN-<instance>-ga_ls / -sa / -rr_ls)*.
- **Heuristic vs exact on the P instances** (p_small, shipped engine, 10 s, 10 runs, K = k): QPSO-noQUBO (tuned) reaches the proven optimum in 10/10 runs on P-n16-k8 (median 0.006 s), 5/10 on P-n19-k2 (mean gap 2.45%; median 0.035 s for the runs that reach it) and 10/10 on P-n22-k8 (median 0.011 s). The MILP (CBC, 600 s) proves optimality only on P-n16-k8, in 209 s. OR-Tools reaches the optimum in 10/10 runs on all three *(E-…)*.
  - The earlier adaptive-α engine reached it in 10/10, 9/10 and 10/10 runs; those rows are archived in `results/runs/p_small.d59_replaced.jsonl`.

## Scaling (scaling_v2: equal conditions, new seeds, 10 runs, 0.6 s per customer capped at 300 s)
Source: `scaling_v2`, QPSO-noQUBO (tuned) vs OR-Tools, all runs through the runner (CPU calibration 2.9–7.4 M ops/s, median 3.5 M), 0 fleet violations, final audit flags 0.

| Instance (n, budget) | QPSO-noQUBO (tuned) | OR-Tools | Holm p |
|---|---|---|---|
| X-n101-k25 (100, 60 s) | **1.87%** | 5.68% | 0.004 |
| X-n200-k36 (199, 120 s) | 3.36% | **3.08%** | 0.004 |
| X-n502-k39 (501, 300 s), cluster-first | 3.00% | **1.42%** | 0.002 |

QPSO-noQUBO (tuned) is ahead at n = 100; OR-Tools is ahead at n = 199 and n = 501 *(S-…, SP-…)*. The cluster-first runs stop at about 0.90 of their budget, because the final repair step reaches a local optimum early.

## Other measured results
- **0 infeasible solutions and 0 fleet-limit violations** in all benchmark tables *(H1, H2)*.
- **Local search is what makes swarm search work on CVRP:** memetic LS lowers the gap by 16.7 points on A-n63-k9 and 16.4 on A-n80-k10 (Holm p = 0.027 on both). No other QPSO component has a significant effect in the ablation *(A-…)*.
- **QUBO formulation:** neal (a classical annealer) returns a feasible route order in 100% of cases and the optimal order on 50–80% of 20 CVRPLIB routes, depending on the penalty weight *(Q0–Q2)*.
- **Road-network local search** on Hyderabad-60: median 128 → 3.0 ms per call (D46) *(D46)*.

## Demo artefacts (one simulated scenario; not benchmarks)
These numbers come from the Hyderabad-60 demo run with the shipped engine (`results/demo/`, `scripts/run_fleet_demo.py`). They describe one scenario under simulated traffic and are shown on the app's Home screen as demo numbers.
- **System-optimal fleet routing:** background delay (externality) falls from 259.7 to 162.1 vehicle-hours (−37.6%) versus naive routing, with platform scale factor S = 25, which is a modelling assumption *(results/demo/metrics.json)*.
- **Time of day:** the same 60 customers have about 114 min of congestion delay when planned at 17:30, versus about 10 min at 03:00 *(result_demo.json, result_0300.json)*.
- **Incident re-routing:** 6.3 min of delay avoided for a simulated incident; the re-routed plan was accepted only because it is cheaper under the new traffic *(incident_demo.json)*.

## Platform differentiators (not benchmarked against OR-Tools)
These are features of the platform. They are not performance claims.
- **System-optimal fleet routing:** the fleet's own traffic is fed into the BPR travel-time model, and routes are planned with marginal cost (it counts the delay imposed on all traffic), iterated with the method of successive averages. Naive, user-equilibrium and system-optimal modes can be compared side by side (`engine/qflux/traffic/fleet_eq.py`, `POST /api/fleet-compare`).
- **Time-dependent multi-objective cost:** travel time, distance, congestion delay and CO₂, with weights and presets (Balanced / Fastest / Greenest / Least congestion). Travel times change with departure time across 7 time-of-day slots (`engine/qflux/core/split.py`, `engine/qflux/traffic/td_matrix.py`).
- **Incident re-routing:** zone or edge incidents raise travel times on the affected roads. Affected vehicles are re-sequenced and re-routed, and the new plan is kept only if it is cheaper under the new traffic (`engine/qflux/dynamic/reroute.py`, `POST /api/scenarios/{id}/incidents`).
- **QUBO module:** route ordering as a QUBO with interchangeable backends (neal simulated annealing, brute force, Held-Karp, 2-opt, D-Wave stub), exposed as an optional slot in QPSO and as `POST /api/quantum/solve-route` (`engine/qflux/quantum/`).
- **Also included:** time-dependent shortest path (Dijkstra / A*) for the ambulance scenario (`engine/qflux/sp/`).

## What we can NOT claim
- **No quantum speedup or quantum advantage.** QPSO is a classical algorithm inspired by quantum mechanics. The QUBO slot ran on a classical simulated annealer.
- **The QUBO slot does not help the search.** QPSO-full (slot on) is significantly worse than QPSO-noQUBO on A-n63, A-n80 and X-n101 in v1, and adding the slot has no significant effect in the ablation.
- **The QUBO solver is slower than classical methods, and not always optimal.** On the same routes, 2-opt found the optimum on 100% of CVRPLIB routes in about 0.03 ms; neal took about 140 ms and found it on 50–80%.
- **No optimality guarantee.** These are heuristics; gaps are measured against best-known solutions.
- **Traffic is simulated.** Hyderabad uses a road graph with BPR time-of-day profiles, not live traffic data.

## Methods notes
- **Budgets:** time budgets only for the comparisons, because local-search moves are not counted as evaluations (D39). 30 s for n ≤ 80, 60 s for n > 80 (D43); scaling 0.6 s per customer, capped at 300 s (D50).
- **Runs and seeds:** 30 runs per (algorithm, instance) in confirm_d54 and bench_core_v1; 10 in the ablation, α sweep, scaling and P runs. Within a table, every algorithm sees the same seeds.
- **Tuning (D54):** α for QPSO-noQUBO and (w, c1, c2) for PSO+LS, 3 configurations each, chosen on the static CVRPLIB tuning instances A-n44-k6 and A-n69-k9 only, under a rule fixed in advance. The choice was committed before the confirmation run. The Hyderabad and SynthCity road-network instances use the same α = 0.3 without separate tuning.
- **Fleet limit:** Augerat A/P instances use exactly k vehicles, because their published optima assume it; CMT and X instances have no limit (D38). Runs over the limit get no gap and are counted.
- **CPU calibration of the runner-launched tables:** every run is at least 2.7 M ops/s (background-throttled runs measured about 1.45 M). Nine runs fall between 2.70 and 2.99 M, under the 3.0 M check threshold: 3 in scaling_v2 and 6 in p_small (mostly the PSO+LS and OR-Tools rows). The throughput audit (0.75× rule) flags none of them. They are reported here, not re-run.
- **CPU conditions (D57):** Windows throttled background-launched processes to about 2.3–2.5× less CPU. Every comparison above is between runs launched the same way. confirm_d54, scaling_v2 and p_small ran via the standalone runner; bench_core_v1 and the ablation ran with all rows throttled. Since D57 the runner is the only way to run experiments (`docs/RUNNING_EXPERIMENTS.md`).
  - Minor caveat: 26 D51 replacement runs in bench_core_v1, the ablation and the α sweep ran faster than their peers.
  - bench_core_v1's OR-Tools rows are excluded from its table for this reason; OR-Tools is compared in confirm_d54.
- **Hardware:** one i7-1360P laptop (4 performance + 8 efficiency cores), Balanced power plan, 11 parallel single-threaded workers. Per-run speed varied up to about 1.26–1.29× on the hybrid CPU (D44); algorithms were interleaved per seed.
- **Memory audit (D51):** runs slowed by low memory were re-run with the same seeds; the final audits flag 0.
- **Fixes applied before the final numbers:**
  - local search uses exact O(1) delta costs (D41; identical results);
  - OR-Tools costs registered as a C++ matrix (D55);
  - road-network local search (D46) is not identical to the exact kernel: final cost ratio 1.0022 on average per tour.
