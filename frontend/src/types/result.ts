// Frozen Result JSON contract (master doc §5.5). Do not change without updating §5 + Decision Log.
export interface ResultJSON {
  job_id: string; scenario_id: string; algorithm: string; seed: number;
  status: "COMPLETED" | "COMPLETED_PARTIAL";
  weights: { wT: number; wD: number; wC: number; wE: number; lam: number };
  kpis: { total_time_min: number; total_distance_km: number; congestion_delay_min: number;
          co2_kg: number; vehicles_used: number; fleet_limit: number | null;
          fitness: number; runtime_s: number; evals: number; feasible: boolean };
  routes: Array<{
    vehicle: number; stops: number[]; load: number; capacity: number;
    time_min: number; distance_km: number; congestion_delay_min: number; co2_kg: number;
    depart_min: number; return_min: number;
    geometry: [number, number][];          // lat/lon polyline along roads
    color: string;
  }>;
  edge_flows?: Array<{ geometry: [number, number][]; fleet_flow: number; vc_ratio: number }>;
  explanation: string[];                   // deterministic sentences (§7.14)
  convergence: Array<{ iter: number; evals: number; best_F: number }>;
  refs: { T: number; D: number; C: number; E: number };
  meta: { config_hash: string; instance: string; tau0: number };
}

// FleetResult = ResultJSON + fleet metrics (§5.5)
export interface FleetResult extends ResultJSON {
  externality_veh_h: number;
  max_vc: number;
  edges_over_capacity: number;
  corridors_used: number;
}

export type FleetMode = "naive" | "user_eq" | "system_opt";

export interface FleetCompareResponse {
  modes: Partial<Record<FleetMode, FleetResult>>;
}

export interface ShortestPathResponse {
  path_geometry: [number, number][];
  eta_min: number;
  cost: number;
  runtime_s: number;
  gap_pct?: number;
  path_times_min?: number[];               // minutes after departure at each path point (D60, additive)
  halfway_by_time?: [number, number];      // path point at ~50% of the travel time (D60, additive)
}
