# QuantumRoute: results summary (2026-10-04)

All numbers come from `results/tables/`; every quotable number has an ID in `results/SLIDE_NUMBERS.md`.
Gaps are % above the best-known solution. "Significant" means Holm–Bonferroni-corrected Wilcoxon p < 0.05 within that table.

## What we can claim

1. **Among the metaheuristics we built, the default engine QPSO-noQUBO is the strongest or tied.** At equal wall-clock time (30 runs per instance), it is significantly better than GA+LS on 4 of 6 core instances, than SA on 6/6, than the random-restart control RR+LS on 5/6, and than QPSO-full on 3/6. It is never significantly worse than any of them, and it is not significantly different from PSO+LS on any instance. Friedman average rank at 30 s: QPSO-noQUBO 2.63, PSO+LS 3.00, QPSO-full 3.38, RR+LS 4.75, GA+LS 6.00, SA 6.75. *(bench_core_v1_wilcoxon_qpso_noqubo.csv, bench_core_v1_friedman.csv)*
2. **Mean gaps of QPSO-noQUBO:** A-n32 0.00%, A-n63 2.07%, A-n80 4.45%, CMT1 0.005% (30 s); CMT5 10.90%, X-n101 2.66% (60 s). 0 infeasible solutions and 0 fleet-limit violations in 1,260 runs. *(bench_core_v1_summary.csv, bench_core_v1_meta.json)*
3. **Local search is what makes swarm search work on CVRP.** In the ablation, memetic local search lowers the gap by 16.7 points on A-n63 and 16.4 on A-n80 (Holm p = 0.027 on both). No other QPSO component (rank mbest, Sobol, adaptive α, tunneling, QUBO slot, diversity re-init) has a significant effect. *(ablation_chain.csv)*
4. **Heuristics reach proven optima fast on the small instances.** Within 10 s, QPSO-noQUBO hits the proven optimum in 10/10, 9/10 and 10/10 runs on P-n16, P-n19 and P-n22, with a median under 0.05 s. The exact MILP (CBC, 600 s) proves optimality only on P-n16 (209 s); on the other two it stops at the time limit with a ≈29% optimality gap (best found 9.4% and 0.5% above the optimum). *(p_vs_exact.csv, milp_p_instances.csv)*
5. **It scales to 500 customers with stated budgets** (0.6 s per customer, capped at 300 s): QPSO 3.02% at n = 100 (60 s) and 3.85% at n = 199 (120 s); cluster-first QPSO 3.40% at n = 501 (300 s). *(scaling_summary.csv)*
6. **The QUBO formulation is correct and ready for a sampler.** A classical annealer (neal) returned a feasible route order in 100% of cases and the optimal order in 50–80% of 20 CVRPLIB routes, depending on the penalty weight. *(qubo_validation.csv)*
7. **Road-network demos run fast:** local search on Hyderabad-60 takes a median 3.0 ms per call instead of 128 ms (D46). *(d46_td_ls_speed.csv)*

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
