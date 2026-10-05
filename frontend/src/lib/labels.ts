// Display names for engine / algorithm keys (wording agreed in results/RESULTS_SUMMARY.md, D59).
// Keys come from job results (`algorithm`) and benchmark tables (`algo`).
export const ALGO_LABELS: Record<string, string> = {
  qpso: "QPSO (quantum-behaved PSO)",
  qpso_noqubo_tuned: "QPSO-noQUBO (tuned)",
  qn_tuned: "QPSO-noQUBO (tuned)",
  qn_tuned_cluster: "QPSO-noQUBO (tuned), cluster-first",
  qpso_noqubo: "QPSO-noQUBO (adaptive α)",
  qpso_full: "QPSO-full (QUBO slot on)",
  qpso_noqubo_linear: "QPSO-noQUBO (custom α schedule)",
  qpso_tuned_qubo: "QPSO-noQUBO (tuned) + QUBO slot",
  qpso_linear_qubo: "QPSO (custom α schedule) + QUBO slot",
  pso: "PSO",
  pso_ls: "PSO+LS",
  pso_tuned: "PSO+LS (tuned)",
  ga: "GA",
  ga_ls: "GA+LS",
  sa: "Simulated annealing",
  rr_ls: "Random restart + LS (control)",
  ortools: "OR-Tools (industry reference)",
  milp: "MILP (CBC)",
  // ablation chain / supporting tables (keys as exported in results/)
  a0_base: "A0 base",
  a1_rank_mbest: "A1 rank mbest",
  a2_sobol: "A2 Sobol init",
  a3_adaptive_alpha: "A3 adaptive α",
  a4_memetic_ls: "A4 memetic LS",
  a5_tunneling: "A5 tunneling",
  a6_qubo: "A6 QUBO slot",
  a7_full: "A7 full",
  qpso_base_plain: "QPSO base (no LS)",
  pso_plain: "PSO (no LS)",
};

export function algoLabel(key: string | null | undefined): string {
  if (!key) return "";
  if (key.endsWith("+reroute")) return `${algoLabel(key.slice(0, -"+reroute".length))} + incident re-routing`;
  return ALGO_LABELS[key] ?? key;
}
