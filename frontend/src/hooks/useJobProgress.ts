// Live job progress: WebSocket /ws/jobs/{id}; on error/close before completion falls back to
// polling GET /jobs/{id} every 2 s (T38). Demo mode replays result_demo.json convergence over ~3 s.
import { useEffect, useRef, useState } from "react";
import { ApiError, getConvergence, getJob, getResultDemo, jobSocketUrl } from "../api/client";
import type { ConvergencePoint, JobStatus } from "../api/types";
import { isDemoMode } from "../lib/demoMode";

export type Transport = "idle" | "websocket" | "polling" | "demo";

export interface JobProgress {
  status: JobStatus | null;
  points: ConvergencePoint[];
  progress: number | null; // 0..1
  error: string | null;
  transport: Transport;
  done: boolean;
}

const TERMINAL = new Set(["COMPLETED", "COMPLETED_PARTIAL", "FAILED", "CANCELLED"]);
const POLL_MS = 2000;
const DEMO_REPLAY_MS = 3000;

interface WsEvent {
  type: "progress" | "completed" | "failed";
  iter?: number;
  evals?: number;
  best_F?: number;
  message?: string;
  status?: string;
}

const initial: JobProgress = { status: null, points: [], progress: null, error: null, transport: "idle", done: false };

function normProgress(p: number | null | undefined): number | null {
  if (p == null || !Number.isFinite(p)) return null;
  return p > 1 ? Math.min(1, p / 100) : Math.max(0, p);
}

export function useJobProgress(jobId: string | null, expectedEvals?: number | null): JobProgress {
  const [state, setState] = useState<JobProgress>(initial);
  const expectedRef = useRef(expectedEvals);
  expectedRef.current = expectedEvals;

  useEffect(() => {
    if (!jobId) {
      setState(initial);
      return;
    }
    let cancelled = false;
    let ws: WebSocket | null = null;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let replayTimer: ReturnType<typeof setInterval> | null = null;
    let finished = false;
    const ctrl = new AbortController();

    const set = (patch: Partial<JobProgress> | ((s: JobProgress) => Partial<JobProgress>)) => {
      if (cancelled) return;
      setState((s) => ({ ...s, ...(typeof patch === "function" ? patch(s) : patch) }));
    };

    const finish = async (status: JobStatus, error: string | null = null) => {
      if (finished) return;
      finished = true;
      if (pollTimer) clearInterval(pollTimer);
      if (ws) {
        ws.onclose = null;
        ws.onerror = null;
        try {
          ws.close();
        } catch {
          /* ignore */
        }
      }
      set({ status, done: true, error, progress: status === "FAILED" ? null : 1 });
      if (status === "COMPLETED" || status === "COMPLETED_PARTIAL") {
        try {
          const pts = await getConvergence(jobId, { silent: true, signal: ctrl.signal });
          if (pts?.length) set({ points: pts });
        } catch {
          /* keep streamed points */
        }
      }
    };

    setState({ ...initial, status: "QUEUED" });

    // ---------------- demo: replay precomputed convergence
    if (isDemoMode()) {
      set({ transport: "demo", status: "RUNNING" });
      getResultDemo({ signal: ctrl.signal })
        .then((r) => {
          const all = r.convergence ?? [];
          if (all.length === 0) {
            finished = true;
            set({ status: r.status, done: true, progress: 1 });
            return;
          }
          const stepMs = Math.max(30, DEMO_REPLAY_MS / all.length);
          let i = 0;
          replayTimer = setInterval(() => {
            i += 1;
            set({ points: all.slice(0, i), progress: i / all.length });
            if (i >= all.length) {
              if (replayTimer) clearInterval(replayTimer);
              finished = true;
              set({ status: r.status, done: true, progress: 1 });
            }
          }, stepMs);
        })
        .catch((e) => {
          finished = true;
          set({ status: "FAILED", done: true, error: String(e?.message ?? e) });
        });
      return () => {
        cancelled = true;
        ctrl.abort();
        if (replayTimer) clearInterval(replayTimer);
      };
    }

    // ---------------- live: polling fallback
    const startPolling = () => {
      if (finished || pollTimer || cancelled) return;
      set({ transport: "polling" });
      const tick = async () => {
        try {
          const j = await getJob(jobId, { silent: true, signal: ctrl.signal });
          set({ status: j.status, progress: normProgress(j.progress) });
          if (TERMINAL.has(String(j.status))) await finish(j.status, j.error_message);
          else {
            // Keep the chart moving while polling (convergence may be available mid-run).
            try {
              const pts = await getConvergence(jobId, { silent: true, signal: ctrl.signal });
              if (Array.isArray(pts) && pts.length) set({ points: pts });
            } catch {
              /* 409/404 before first points is fine */
            }
          }
        } catch (e) {
          if ((e as Error)?.name === "AbortError") return;
          if (e instanceof ApiError && e.status === 404) {
            await finish("FAILED", "Job not found (404)");
            return;
          }
          set({ error: String((e as Error)?.message ?? e) });
        }
      };
      void tick();
      pollTimer = setInterval(tick, POLL_MS);
    };

    // ---------------- live: WebSocket first
    try {
      ws = new WebSocket(jobSocketUrl(jobId));
      set({ transport: "websocket" });
      ws.onmessage = (msg) => {
        let ev: WsEvent;
        try {
          ev = JSON.parse(String(msg.data));
        } catch {
          return;
        }
        if (ev.type === "progress") {
          set((s) => {
            const pts =
              ev.iter != null && ev.evals != null && ev.best_F != null
                ? [...s.points, { iter: ev.iter, evals: ev.evals, best_F: ev.best_F }]
                : s.points;
            const exp = expectedRef.current;
            return {
              status: "RUNNING",
              points: pts,
              progress: exp && ev.evals != null ? Math.min(0.99, ev.evals / exp) : s.progress,
            };
          });
        } else if (ev.type === "completed") {
          void finish((ev.status as JobStatus) ?? "COMPLETED");
        } else if (ev.type === "failed") {
          void finish("FAILED", ev.message ?? "Job failed");
        }
      };
      ws.onerror = () => startPolling();
      ws.onclose = () => {
        if (!finished) startPolling();
      };
    } catch {
      startPolling();
    }

    return () => {
      cancelled = true;
      ctrl.abort();
      if (pollTimer) clearInterval(pollTimer);
      if (ws) {
        ws.onclose = null;
        ws.onerror = null;
        ws.onmessage = null;
        try {
          ws.close();
        } catch {
          /* ignore */
        }
      }
    };
  }, [jobId]);

  return state;
}
