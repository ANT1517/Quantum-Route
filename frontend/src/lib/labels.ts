// Display names for engine / algorithm keys (wording agreed in results/RESULTS_SUMMARY.md, D59).
// Keys come from job results (`algorithm`) and benchmark tables (`algo`).
export const ALGO_LABELS: Record<string, string> = {
  qpso: "QPSO (quantum-behaved PSO)",
  qpso_noqubo_tuned: "QPSO-noQUBO (tuned)",
  qn_tuned: "QPSO-noQUBO (tuned)",
  qn_tuned_cluster: "QPSO-noQUBO (tuned), cluster-first",
  qpso_noqubo: "QPSO-noQUBO (adaptive α)",
  qpso_full: "QPSO-full (QUBO slot on)",
  pso: "PSO",
  pso_ls: "PSO+LS",
  pso_tuned: "PSO+LS (tuned)",
  ga: "GA",
  ga_ls: "GA+LS",
  sa: "Simulated annealing",
  rr_ls: "Random restart + LS (control)",
  ortools: "OR-Tools (industry reference)",
  milp: "MILP (CBC)",
};

export function algoLabel(key: string | null | undefined): string {
  if (!key) return "";
  if (key.endsWith("+reroute")) return `${algoLabel(key.slice(0, -"+reroute".length))} + incident re-routing`;
  return ALGO_LABELS[key] ?? key;
}
