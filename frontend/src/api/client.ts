// Typed API client for §5.4 (base /api). Errors {"error":{"code","message"}} become ApiError + toast.
// Demo mode (VITE_DEMO_MODE=true or the header toggle) reads static /demo/*.json instead.
import type { FleetCompareResponse, ResultJSON, ShortestPathResponse } from "../types/result";
import { isDemoMode } from "../lib/demoMode";
import { notify } from "../lib/toast";
import type {
  AddIncidentResponse,
  BenchmarkListItem,
  BenchmarkTable,
  ConvergencePoint,
  CreateJobRequest,
  CreateJobResponse,
  CreateScenarioRequest,
  FleetCompareRequest,
  FleetDemo,
  Health,
  HomeKpi,
  Incident,
  IncidentDemo,
  JobInfo,
  QuboRouteDemo,
  QuboValidation,
  ScenarioDetail,
  ScenarioSummary,
  ShortestPathDemo,
  ShortestPathRequest,
  SolveRouteRequest,
  SolveRouteResponse,
} from "./types";

export const API_BASE = "/api";
const BASE_URL: string = import.meta.env.BASE_URL ?? "/";

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export interface RequestOptions {
  /** Do not raise a toast (caller shows the error inline). */
  silent?: boolean;
  signal?: AbortSignal;
}

function report(err: ApiError, opts?: RequestOptions) {
  if (!opts?.silent) notify(`${err.code}: ${err.message}`, "error");
}

async function parseError(res: Response): Promise<ApiError> {
  let code = `HTTP_${res.status}`;
  let message = res.statusText || "Request failed";
  try {
    const body = await res.json();
    if (body && typeof body === "object" && body.error) {
      code = String(body.error.code ?? code);
      message = String(body.error.message ?? message);
    } else if (body && typeof body === "object" && "detail" in body) {
      message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    }
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(res.status, code, message);
}

async function request<T>(method: string, path: string, body?: unknown, opts?: RequestOptions): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: opts?.signal,
    });
  } catch (e) {
    if ((e as Error)?.name === "AbortError") throw e;
    const err = new ApiError(0, "NETWORK", "Backend unreachable. Switch on demo mode to use offline data.");
    report(err, opts);
    throw err;
  }
  if (!res.ok) {
    const err = await parseError(res);
    report(err, opts);
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Read a static demo file from public/demo/. */
export async function demoFile<T>(name: string, opts?: RequestOptions): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}demo/${name}`, { signal: opts?.signal });
  } catch (e) {
    if ((e as Error)?.name === "AbortError") throw e;
    const err = new ApiError(0, "DEMO_FILE", `Could not load demo file ${name}`);
    report(err, opts);
    throw err;
  }
  const ct = res.headers.get("content-type") ?? "";
  if (!res.ok || ct.includes("text/html")) {
    const err = new ApiError(res.ok ? 404 : res.status, "DEMO_FILE_MISSING", `Demo file ${name} not found`);
    report(err, opts);
    throw err;
  }
  return (await res.json()) as T;
}

const demo = () => isDemoMode();

// ------------------------------------------------------------------ P0 endpoints

export function health(opts?: RequestOptions): Promise<Health> {
  if (demo()) return Promise.resolve({ status: "demo", version: "demo-mode (static JSON)" });
  return request<Health>("GET", "/health", undefined, opts);
}

export function listScenarios(opts?: RequestOptions): Promise<ScenarioSummary[]> {
  if (demo()) return demoFile<ScenarioSummary[]>("scenarios.json", opts);
  return request("GET", "/scenarios", undefined, opts);
}

export async function createScenario(req: CreateScenarioRequest, opts?: RequestOptions): Promise<{ scenario: ScenarioSummary }> {
  if (demo()) {
    // Demo: no server-side generation; hand back the pre-exported demo scenario.
    const d = await demoFile<ScenarioDetail>("scenario_demo.json", opts);
    return { scenario: d.scenario };
  }
  return request("POST", "/scenarios", req, opts);
}

export function getScenario(id: string, opts?: RequestOptions): Promise<ScenarioDetail> {
  if (demo()) return demoFile<ScenarioDetail>("scenario_demo.json", opts);
  return request("GET", `/scenarios/${encodeURIComponent(id)}`, undefined, opts);
}

export async function addIncident(scenarioId: string, incident: Incident, opts?: RequestOptions): Promise<AddIncidentResponse> {
  if (demo()) {
    await demoFile<IncidentDemo>("incident_demo.json", opts);
    return { incident_id: "MOCK-demo-incident", affected_edges: [] };
  }
  return request("POST", `/scenarios/${encodeURIComponent(scenarioId)}/incidents`, incident, opts);
}

export async function createJob(req: CreateJobRequest, opts?: RequestOptions): Promise<CreateJobResponse> {
  if (demo()) {
    const r = await demoFile<ResultJSON>("result_demo.json", opts);
    return { job_id: req.warm_start_job_id ? `${r.job_id}-reopt` : r.job_id, status: "QUEUED" };
  }
  return request("POST", "/jobs", req, opts);
}

export async function getJob(id: string, opts?: RequestOptions): Promise<JobInfo> {
  if (demo()) return { status: "COMPLETED", progress: 1, error_message: null };
  return request("GET", `/jobs/${encodeURIComponent(id)}`, undefined, opts);
}

export async function getJobResult(id: string, opts?: RequestOptions): Promise<ResultJSON> {
  if (demo()) {
    if (id.endsWith("-reopt")) return (await demoFile<IncidentDemo>("incident_demo.json", opts)).after;
    return demoFile<ResultJSON>("result_demo.json", opts);
  }
  return request("GET", `/jobs/${encodeURIComponent(id)}/result`, undefined, opts);
}

export async function getConvergence(id: string, opts?: RequestOptions): Promise<ConvergencePoint[]> {
  if (demo()) return (await getJobResult(id, opts)).convergence;
  return request("GET", `/jobs/${encodeURIComponent(id)}/convergence`, undefined, opts);
}

export async function cancelJob(id: string, opts?: RequestOptions): Promise<{ status: string }> {
  if (demo()) return { status: "CANCELLED" };
  return request("POST", `/jobs/${encodeURIComponent(id)}/cancel`, undefined, opts);
}

/**
 * POST /shortest-path. `demoIncident` only matters in demo mode: it selects the precomputed
 * "after incident" path from shortest_path_demo.json (live mode uses the scenario's incidents).
 */
export async function shortestPath(
  req: ShortestPathRequest,
  opts?: RequestOptions & { demoIncident?: boolean },
): Promise<ShortestPathResponse> {
  if (demo()) {
    const d = await demoFile<ShortestPathDemo>("shortest_path_demo.json", opts);
    return opts?.demoIncident ? d.after : d.before;
  }
  return request("POST", "/shortest-path", req, opts);
}

export async function fleetCompare(req: FleetCompareRequest, opts?: RequestOptions): Promise<FleetCompareResponse> {
  if (demo()) {
    const d = await demoFile<FleetDemo>("fleet_demo.json", opts);
    return { modes: d.modes };
  }
  return request("POST", "/fleet-compare", req, opts);
}

export function listBenchmarks(opts?: RequestOptions): Promise<Array<BenchmarkListItem | string>> {
  if (demo()) return demoFile("benchmarks.json", opts);
  return request("GET", "/benchmarks", undefined, opts);
}

export function getBenchmark(name: string, opts?: RequestOptions): Promise<BenchmarkTable> {
  if (demo()) return demoFile(`benchmark_${name}.json`, opts);
  return request("GET", `/benchmarks/${encodeURIComponent(name)}`, undefined, opts);
}

export function quantumValidation(opts?: RequestOptions): Promise<QuboValidation> {
  if (demo()) return demoFile("qubo_validation.json", opts);
  return request("GET", "/quantum/validation", undefined, opts);
}

export async function solveRouteQubo(req: SolveRouteRequest, opts?: RequestOptions): Promise<SolveRouteResponse> {
  if (demo()) return demoFile<QuboRouteDemo>("qubo_route_demo.json", opts);
  return request("POST", "/quantum/solve-route", req, opts);
}

/** URL for a figure/CSV served by GET /files/{path} (or the demo folder in demo mode). */
export function fileUrl(path: string): string {
  if (/^(https?:|data:|blob:)/.test(path) || path.startsWith("/")) return path;
  const clean = path.replace(/^\.?\/+/, "");
  if (demo()) return `${BASE_URL}demo/${clean}`;
  return `${API_BASE}/files/${clean.split("/").map(encodeURIComponent).join("/")}`;
}

// ------------------------------------------------------------------ demo-file helpers

export const getHomeKpis = (opts?: RequestOptions) => demoFile<HomeKpi[]>("home_kpis.json", opts);
export const getIncidentDemo = (opts?: RequestOptions) => demoFile<IncidentDemo>("incident_demo.json", opts);
export const getFleetDemo = (opts?: RequestOptions) => demoFile<FleetDemo>("fleet_demo.json", opts);
export const getShortestPathDemo = (opts?: RequestOptions) => demoFile<ShortestPathDemo>("shortest_path_demo.json", opts);
export const getQuboRouteDemo = (opts?: RequestOptions) => demoFile<QuboRouteDemo>("qubo_route_demo.json", opts);
export const getResultDemo = (opts?: RequestOptions) => demoFile<ResultJSON>("result_demo.json", opts);

/** WebSocket URL for /ws/jobs/{id} relative to the current host (Vite proxies /ws in dev). */
export function jobSocketUrl(id: string): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/ws/jobs/${encodeURIComponent(id)}`;
}
