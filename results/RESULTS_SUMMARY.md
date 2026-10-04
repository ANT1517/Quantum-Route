# QuantumRoute: results summary (2026-10-04)

All numbers come from `results/tables/`; every quotable number has an ID in `results/SLIDE_NUMBERS.md`.
Gaps are % above the best-known solution. "Significant" means Holm–Bonferroni-corrected Wilcoxon p < 0.05 within that table.

> **Known issue (D57), resolution pending.** Experiments launched in the background ran with ≈2.3–2.5× less CPU than those started by the standalone runner (per-run CPU calibration). Inside one group the comparisons are fair. The OR-Tools rows of bench_core_v1 and scaling (re-run after the D55 fix) ran at full speed, while the other algorithms in those tables ran throttled, so **claim 3 and the OR-Tools comparisons under Scaling below favour OR-Tools and must not be quoted until they are re-run under equal conditions.** The D54 confirmation (below) ran all algorithms under the same conditions.

## Headline claims
(bench_core_v1: 30 runs per algorithm and instance; 30 s for n <= 80, 60 s for CMT5 and X-n101; "significant" = Holm-corrected p < 0.05. IDs refer to `SLIDE_NUMBERS.md`.)

1. **QPSO-noQUBO significantly beats GA+LS, SA and random-restart+LS:**
   - **GA+LS** on A-n32-k5, A-n63-k9, A-n80-k10 and CMT1 *(PN-<instance>-ga_ls)*;
   - **SA** on all six core instances *(PN-<instance>-sa)*;
   - **random-restart+LS** on A-n63-k9, A-n80-k10, CMT1, CMT5 and X-n101-k25 *(PN-<instance>-rr_ls)*.
2. **Statistically level with PSO+LS.** There is no significant difference on any instance; the smallest Holm-corrected p is 0.141, on CMT1 *(PN-<instance>-pso_ls)*.
3. **[Confounded, D57; do not quote]** **Google OR-Tools (industry reference, C++) is ahead** on A-n63-k9 (1.54% vs 2.07%), A-n80-k10 (1.93% vs 4.45%), CMT1 (0.000% vs 0.005%) and CMT5 (7.60% vs 10.90%). QPSO-noQUBO is ahead on X-n101-k25 (2.66% vs 5.45%). They are tied on A-n32-k5 (0.00% each) *(G-<instance>-ortools, G-<instance>-qpso_noqubo, PN-<instance>-ortools)*.
4. **Reaches the proven optimum on the P instances** in 10/10 (P-n16-k8), 9/10 (P-n19-k2) and 10/10 (P-n22-k8) runs, with a median time to the optimum ≤ 0.05 s (0.009, 0.046 and 0.015 s). The MILP proves optimality only on P-n16-k8, in 209 s *(E-P-n16-k8-*, E-P-n19-k2-*, E-P-n22-k8-*)*.

## D54 confirmatory round (same launch conditions for all algorithms, new seeds)
- **Tuning:** on A-n44-k6 and A-n69-k9 only, 3 configurations each, under a rule fixed in advance. It chose fixed α = 0.3 for QPSO-noQUBO and the current (w, c1, c2) for PSO+LS. The choice was committed before the confirmation run (`configs/experiments/d54_choice.yaml`).
- **Confirmation:** 30 runs per algorithm and instance, seeds 65345–71374, bench_core budgets. Holm correction over 18 comparisons; 0 infeasible; 0 fleet violations; final throughput audit flags 0.
- **Pre-committed rule result:** tuned QPSO-noQUBO is **significantly better than tuned PSO+LS on A-n63-k9, A-n80-k10, CMT5 and X-n101-k25** (Holm p = 0.018, < 0.001, < 0.001 and 0.013). The mean paired differences are −0.33, −2.11, −1.72 and −0.28 gap points *(CP-<instance>-pso_tuned)*. It is not significantly different on A-n32-k5 (1.28% vs 0.00%, Holm p = 0.056) or CMT1 (0.26% vs 0.05%, Holm p = 0.080), where its mean is the worse of the two.
- **Against OR-Tools under equal launch conditions:**
  - tuned QPSO-noQUBO is significantly better on A-n63-k9 (0.94% vs 1.55%), A-n80-k10 (1.18% vs 1.71%) and X-n101-k25 (1.83% vs 5.59%);
  - OR-Tools is significantly better on CMT1 (0.00% vs 0.26%);
  - no significant difference on A-n32-k5 or CMT5 *(C-…, CP-<instance>-ortools)*.
- **Default α unchanged.** The confirmation did not include the default (adaptive α) arm on the new seeds, so it shows no improvement over the default. The pre-committed rule keeps adaptive α as the app default. Comparing these numbers with bench_core_v1 is not valid (D57: different CPU conditions).

## Other measured results
- **0 infeasible solutions and 0 fleet-limit violations** in the 1,260 bench_core_v1 runs *(H1, H2)*.
- **Local search is what makes swarm search work on CVRP:** the memetic LS row of the ablation lowers the gap by 16.7 points on A-n63-k9 and 16.4 on A-n80-k10 (Holm p = 0.027 on both). No other QPSO component has a significant effect *(A-<instance>-a4_memetic_ls and the other A- rows)*.
- **Scaling** (0.6 s per customer, capped at 300 s; the OR-Tools numbers are confounded, D57):
  - n = 100 (60 s): QPSO 3.02%, OR-Tools 5.45%;
  - n = 199 (120 s): QPSO 3.85%, OR-Tools 3.08%;
  - n = 501 (300 s): cluster-first QPSO 3.40%, OR-Tools 1.43% *(S-…)*.
- **QUBO formulation:** neal (a classical annealer) returns a feasible route order in 100% of cases and the optimal order on 50–80% of 20 CVRPLIB routes, depending on the penalty weight *(Q0–Q2)*.
- **Road-network local search** on Hyderabad-60: median 128 → 3.0 ms per call (D46) *(D46)*.

## Platform differentiators (not benchmarked against OR-Tools)
These are features of the platform. They are not performance claims.
- **System-optimal fleet routing:** the fleet's own traffic is fed into the BPR travel-time model, and routes are planned with marginal cost (it counts the delay imposed on all traffic), iterated with the method of successive averages. Naive, user-equilibrium and system-optimal modes can be compared side by side (`engine/qflux/traffic/fleet_eq.py`, `POST /api/fleet-compare`).
- **Time-dependent multi-objective cost:** travel time, distance, congestion delay and CO₂, with weights and presets (Balanced / Fastest / Greenest / Least congestion). Travel times change with departure time across 7 time-of-day slots (`engine/qflux/core/split.py`, `engine/qflux/traffic/td_matrix.py`).
- **Incident re-routing:** zone or edge incidents raise travel times on the affected roads. Affected vehicles are re-sequenced and re-routed, and the new plan is kept only if it is cheaper under the new traffic (`engine/qflux/dynamic/reroute.py`, `POST /api/scenarios/{id}/incidents`).
- **QUBO module:** route ordering as a QUBO with interchangeable backends (neal simulated annealing, brute force, Held-Karp, 2-opt, D-Wave stub), exposed as an optional slot in QPSO and as `POST /api/quantum/solve-route` (`engine/qflux/quantum/`).
- **Also included:** time-dependent shortest path (Dijkstra / A*) for the ambulance scenario (`engine/qflux/sp/`).

## What we can NOT claim

- **No quantum speedup or quantum advantage.** QPSO is a classical algorithm inspired by quantum mechanics. The QUBO slot ran on a classical simulated annealer.
- **QPSO is not better than PSO.** With local search, QPSO-noQUBO and PSO+LS are statistically indistinguishable on all 6 instances. Without local search, at equal evaluations, plain QPSO is worse than plain PSO on A-n80 (144.2% vs 125.5%, Holm p = 0.004); on A-n63 the difference is not significant. *(ablation_evals_summary.csv)*
- **The QUBO slot does not help the search.** QPSO-full is significantly worse than QPSO-noQUBO on A-n63, A-n80 and X-n101, and adding the slot has no significant effect in the ablation.
- **The QUBO solver is slower than classical methods, and not always optimal.** On the same routes, 2-opt found the optimum on 100% of CVRPLIB routes in about 0.03 ms; neal took about 140 ms and found it on 50–80%.
- **We do not beat OR-Tools in general.** OR-Tools (the industry reference) is significantly better than QPSO-noQUBO on A-n63, A-n80, CMT1 and CMT5 and ranks first at 30 s (1.50). It is also better at n = 199 (3.08% vs 3.85%) and n = 501 (1.43% vs 3.40%). QPSO-noQUBO is better only on X-n101 at 60 s (2.66% vs 5.45%).
- **No optimality guarantee.** These are heuristics; gaps are measured against best-known solutions.
- **Traffic is simulated.** Hyderabad uses a road graph with BPR time-of-day profiles, not live traffic data.

## Methods notes

- **Budgets:** time budgets only for the comparisons, because local-search moves are not counted as evaluations (D39). 30 s for n ≤ 80, 60 s for n > 80 (D43); scaling 0.6 s per customer, capped at 300 s (D50).
- **Runs and seeds:** 30 runs per (algorithm, instance) in bench_core_v1, 10 in the ablation, α sweep, scaling and P runs. Seed = 12345 + 1000 × instance index + run index; every algorithm sees the same seeds.
- **Fleet limit:** Augerat A/P instances use exactly k vehicles, because their published optima assume it; CMT and X instances have no limit (D38). Runs over the limit get no gap and are counted.
- **Hardware:** one i7-1360P laptop (4 performance + 8 efficiency cores), Balanced power plan, 11 parallel single-threaded workers. On the hybrid CPU, per-run speed varied up to about 1.26–1.29× (D44). Algorithms were interleaved per seed, so this is noise, not bias. A pre-registered check pinned to performance cores (D49) was not run.
- **Memory audit (D51):** 25 runs slowed by low memory were re-run with the same seeds (two passes); the final audit flags 0.
- **Fixes applied before the final numbers:**
  - local search uses exact O(1) delta costs (D41; identical results, about 130× faster);
  - OR-Tools costs registered as a C++ matrix (D55; only OR-Tools rows were re-run).
- **Road-network local search (D46)** is not move-for-move identical to the exact kernel: final cost ratio 1.0022 on average per tour.
- **Tuning:** only on the tuning instances A-n44-k6 and A-n69-k9, with at most 4 configurations; never on test instances.
