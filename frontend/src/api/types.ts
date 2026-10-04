// Request/response types for §5.4 endpoints that are NOT part of the frozen result.ts contract.
import type { FleetMode, FleetResult, ResultJSON, ShortestPathResponse } from "../types/result";

export type ScenarioSource = "hyderabad" | "synth" | "cvrplib";
export type Algorithm = "qpso" | "pso" | "ga" | "sa" | "ortools" | "milp" | "qpso_noqubo_tuned" | "qpso_noqubo"
  | "qpso_noqubo_linear" | "qpso_full";
export type JobStatus =
  | "QUEUED"
  | "RUNNING"
  | "COMPLETED"
  | "COMPLETED_PARTIAL"
  | "FAILED"
  | "CANCELLED"
  | string;

export interface Health { status: string; version: string }

export interface ScenarioSummary {
  id: string;
  name: string;
  source: ScenarioSource | string;
  n_customers: number;
  K: number;
  Q: number;
  seed: number;
  tau0: number;
}

export interface CreateScenarioRequest {
  name: string;
  source: ScenarioSource;
  n_customers: number;
  K: number;
  Q: number;
  seed: number;
  tau0: number;
}

export interface Customer { id: number; lat: number; lon: number; demand: number }

export interface ScenarioDetail {
  scenario: ScenarioSummary;
  customers: Customer[];
  depot: { lat: number; lon: number };
}

export interface ZoneIncident {
  type: "zone";
  center: [number, number];
  radius_m: number;
  factor: number;
  start_min: number;
  end_min: number;
}

export interface EdgesIncident {
  type: "edges";
  edge_ids: Array<string | number>;
  factor?: number;
  start_min?: number;
  end_min?: number;
}

export type Incident = ZoneIncident | EdgesIncident;

export interface AddIncidentResponse { incident_id: string; affected_edges: number | unknown[] }

export interface Weights { wT: number; wD: number; wC: number; wE: number }

export interface CreateJobRequest {
  scenario_id: string;
  algorithm: Algorithm;
  weights: Weights;
  params: Record<string, unknown>;
  seed: number;
  budget: { evals: number | null; time_s: number | null };
  fleet_mode: FleetMode;
  warm_start_job_id?: string;
}

export interface CreateJobResponse { job_id: string; status: JobStatus }

export interface JobInfo { status: JobStatus; progress: number | null; error_message: string | null }

export type ConvergencePoint = ResultJSON["convergence"][number];

export interface ShortestPathRequest {
  scenario_id: string;
  source: [number, number];
  target: [number, number];
  depart_min: number;
  algorithm: "dijkstra" | "astar" | "qpso";
  weights?: Partial<Weights>;
}

export interface FleetCompareRequest {
  scenario_id: string;
  modes: FleetMode[];
  S: number;
  weights: Weights;
  seed: number;
}

export interface BenchmarkListItem { name: string; title?: string; [k: string]: unknown }

export interface BenchmarkTable {
  table: Array<Record<string, unknown>>;
  figures: string[];
  meta: { runs?: number | string; budget?: number | string; [k: string]: unknown };
}

export interface QuboValidation { table: Array<Record<string, unknown>> }

export interface SolveRouteRequest { route_stops: number[]; backend: "neal" | "brute" | "2opt" | "qiskit" }

export interface SolveRouteResponse {
  order: number[];
  energy: number;
  feasible: boolean;
  qubo_matrix: number[][];
  time_s?: number;
  optimal_cost?: number;
}

// ---- demo-only files (same names that scripts/export_demo.py will write)
export interface IncidentDemo {
  incident: ZoneIncident;
  before: ResultJSON;
  after: ResultJSON;
  report: {
    accepted: boolean;
    delay_avoided_min: number;
    reopt_time_s: number;
    eta_change: Array<{ vehicle: number; before_min: number; after_min: number }>;
  };
}

export interface FleetDemo { S: number; modes: Partial<Record<FleetMode, FleetResult>> }

export interface ShortestPathDemo {
  source: [number, number];
  target: [number, number];
  depart_min: number;
  before: ShortestPathResponse;
  after: ShortestPathResponse;
  incident: ZoneIncident | null;
  labels?: { source?: string; target?: string };
}

export interface QuboRouteDemo extends SolveRouteResponse { route_stops: number[]; label?: string; backend?: string }

export interface HomeKpi { label: string; value: number | string; unit: string; source: string }
