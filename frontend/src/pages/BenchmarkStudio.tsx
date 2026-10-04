import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fileUrl, getBenchmark, listBenchmarks } from "../api/client";
import BoxPlot from "../components/BoxPlot";
import { Empty, ErrorState, Loading, MockBadge, QueryState } from "../components/States";
import StatsTable from "../components/StatsTable";
import { algoColor } from "../lib/colors";
import { fmt } from "../lib/format";
import { benchmarkKeys, computeVerdict } from "../lib/verdict";

type Row = Record<string, unknown>;

function FigureImg({ src }: { src: string }) {
  const [failed, setFailed] = useState(false);
  if (failed) return <div className="rounded border border-dashed border-slate-300 p-4 text-xs text-slate-500">Figure unavailable: {src}</div>;
  return <img src={fileUrl(src)} alt={src} className="w-full rounded border border-slate-200 bg-white" onError={() => setFailed(true)} />;
}

export default function BenchmarkStudio() {
  const list = useQuery({ queryKey: ["benchmarks"], queryFn: ({ signal }) => listBenchmarks({ signal }) });
  const items = useMemo(
    () => (list.data ?? []).map((x) => (typeof x === "string" ? { name: x, title: x } : { name: String(x.name), title: String(x.title ?? x.name) })),
    [list.data],
  );
  const [name, setName] = useState<string | null>(null);
  useEffect(() => {
    if (!name && items.length) setName(items[0].name);
  }, [items, name]);

  const bench = useQuery({
    queryKey: ["benchmark", name],
    queryFn: ({ signal }) => getBenchmark(name!, { signal }),
    enabled: !!name,
  });

  const rows: Row[] = bench.data?.table ?? [];
  const keys = useMemo(() => benchmarkKeys(rows), [rows]);
  const instances = useMemo(() => (keys.instance ? Array.from(new Set(rows.map((r) => String(r[keys.instance!])))) : []), [rows, keys.instance]);
  const [inst, setInst] = useState<string>("__all");
  useEffect(() => setInst("__all"), [name]);
  const filtered = inst === "__all" || !keys.instance ? rows : rows.filter((r) => String(r[keys.instance!]) === inst);
  const verdict = useMemo(() => computeVerdict(filtered), [filtered]);

  const arrayKey = useMemo(() => {
    if (!filtered.length) return null;
    const ks = Object.keys(filtered[0]);
    return ks.find((k) => filtered.some((r) => Array.isArray(r[k]) && (r[k] as unknown[]).every((v) => typeof v === "number"))) ?? null;
  }, [filtered]);
  const boxInstance = keys.instance ? (inst === "__all" ? instances[0] : inst) : null;
  const boxGroups =
    arrayKey && keys.algorithm
      ? filtered
          .filter((r) => !boxInstance || String(r[keys.instance!]) === boxInstance)
          .map((r) => ({ label: String(r[keys.algorithm!]), values: (r[arrayKey] as number[]) ?? [], color: algoColor(String(r[keys.algorithm!])) }))
      : [];

  const bestPerInstance = useMemo(() => {
    const best = new Set<Row>();
    if (!keys.gap) return best;
    const groups = new Map<string, Row[]>();
    filtered.forEach((r) => {
      const g = keys.instance ? String(r[keys.instance]) : "all";
      groups.set(g, [...(groups.get(g) ?? []), r]);
    });
    groups.forEach((rs) => {
      const valid = rs.filter((r) => typeof r[keys.gap!] === "number");
      if (valid.length) best.add(valid.reduce((a, b) => ((b[keys.gap!] as number) < (a[keys.gap!] as number) ? b : a)));
    });
    return best;
  }, [filtered, keys]);

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap items-center gap-4">
        <h1 className="page-title">Benchmark Studio</h1>
        <QueryState q={list} isEmpty={(d) => d.length === 0} empty={<span className="text-sm text-slate-500">No benchmark tables exported yet.</span>}>
          {() => (
            <select className="input w-auto" value={name ?? ""} onChange={(e) => setName(e.target.value)}>
              {items.map((i) => (
                <option key={i.name} value={i.name}>
                  {i.title}
                </option>
              ))}
            </select>
          )}
        </QueryState>
        {name && <MockBadge text={name} />}
        <Link to="/convergence" className="ml-auto text-sm text-teal-700 underline">
          Convergence overlay →
        </Link>
      </div>

      {name && bench.isLoading && <Loading label="Loading benchmark…" />}
      {bench.isError && <ErrorState error={bench.error} onRetry={() => bench.refetch()} />}
      {bench.data && rows.length === 0 && <Empty title="This benchmark table is empty" />}
      {bench.data && rows.length > 0 && (
        <>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            {keys.instance && (
              <>
                <span className="label mb-0">Instances</span>
                {["__all", ...instances].map((i) => (
                  <button key={i} className={`rounded px-2 py-1 text-xs ${inst === i ? "bg-teal-600 text-white" : "bg-white text-slate-700 ring-1 ring-slate-300"}`} onClick={() => setInst(i)}>
                    {i === "__all" ? "All" : i}
                  </button>
                ))}
              </>
            )}
            <span className="ml-auto text-slate-600">
              Runs: <b>{fmt(bench.data.meta?.runs)}</b> · Budget: <b>{fmt(bench.data.meta?.budget)}</b>
            </span>
          </div>
          <div className="card border-teal-200 bg-teal-50">
            <div className="label text-teal-800">Verdict (computed from the table below)</div>
            <ul className="list-disc space-y-1 pl-5 text-sm text-slate-800">
              {verdict.map((v, i) => (
                <li key={i}>{v}</li>
              ))}
            </ul>
          </div>
          <div className="card">
            <StatsTable
              rows={filtered}
              highlight={(r) => bestPerInstance.has(r)}
              colorFor={(r) => (keys.algorithm ? algoColor(String(r[keys.algorithm])) : undefined)}
              columns={keys.algorithm ? [keys.algorithm, ...Object.keys(filtered[0]).filter((k) => k !== keys.algorithm)] : undefined}
            />
            <div className="mt-2 text-xs text-slate-400">Highlighted: lowest {keys.gap?.replace(/_/g, " ") ?? "value"} per instance.</div>
          </div>
          {boxGroups.length > 0 && (
            <div className="card">
              <div className="label">
                Per-run distribution ({arrayKey}){boxInstance ? ` · ${boxInstance}` : ""}
              </div>
              <BoxPlot groups={boxGroups} unit={arrayKey ?? ""} />
            </div>
          )}
          {bench.data.figures?.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              {bench.data.figures.map((f) => (
                <FigureImg key={f} src={f} />
              ))}
            </div>
          ) : (
            <div className="text-xs text-slate-400">No figures exported for this benchmark.</div>
          )}
        </>
      )}
      <div className="text-xs text-slate-500">
        Within each table every algorithm gets the same time budget and the same seeds; the metaheuristics share one decoder, while OR-Tools
        (industry reference) uses its own C++ model. Heuristics give good solutions, not optimality proofs; if QPSO does not win on an instance,
        the table says so.
      </div>
    </div>
  );
}
