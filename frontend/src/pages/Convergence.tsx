import { useQueries } from "@tanstack/react-query";
import { useState } from "react";
import { getJobResult } from "../api/client";
import ConvergenceChart from "../components/ConvergenceChart";
import { Empty, ErrorState, Loading } from "../components/States";
import { algoLabel } from "../lib/labels";
import { algoColor } from "../lib/colors";
import { useDemoMode } from "../lib/demoMode";
import { useSession } from "../lib/session";

// S8: overlay convergence curves (best F vs evaluations) of several finished jobs.
export default function Convergence() {
  const demo = useDemoMode();
  const session = useSession();
  const [text, setText] = useState(session.lastJobId ?? (demo ? "demo" : ""));
  const [ids, setIds] = useState<string[]>(text ? [text] : []);

  const qs = useQueries({
    queries: ids.map((id) => ({
      queryKey: ["result", id],
      queryFn: ({ signal }: { signal: AbortSignal }) => getJobResult(id, { signal, silent: true }),
    })),
  });

  const series = qs
    .map((q, i) => (q.data ? { name: `${algoLabel(q.data.algorithm)} · ${ids[i]}`, color: algoColor(q.data.algorithm), points: q.data.convergence } : null))
    .filter((s): s is NonNullable<typeof s> => s !== null);

  return (
    <div className="space-y-4">
      <div className="card space-y-2">
        <h1 className="page-title">Convergence overlay</h1>
        <label className="label">Job ids (comma-separated)</label>
        <div className="flex gap-2">
          <input className="input" value={text} onChange={(e) => setText(e.target.value)} placeholder="job ids…" />
          <button
            className="btn-primary"
            onClick={() =>
              setIds(
                text
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean),
              )
            }
          >
            Load
          </button>
        </div>
        {demo && <div className="text-xs text-slate-500">Demo mode: every id resolves to result_demo.json.</div>}
      </div>
      {ids.length === 0 ? (
        <Empty title="No jobs selected" />
      ) : qs.some((q) => q.isLoading) ? (
        <Loading />
      ) : (
        <div className="card">
          {qs.map((q, i) => (q.isError ? <ErrorState key={ids[i]} error={q.error} onRetry={() => q.refetch()} /> : null))}
          <ConvergenceChart series={series} height={380} />
          <div className="mt-2 text-xs text-slate-500">Median ± IQR bands across seeds come from the exported figures in Benchmark Studio.</div>
        </div>
      )}
    </div>
  );
}
