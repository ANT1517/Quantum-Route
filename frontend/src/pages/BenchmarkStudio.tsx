import { useQuery } from "@tanstack/react-query";
import { Atom, BarChart3, FlaskConical, Layers, Scale, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fileUrl, getBenchmark, listBenchmarks, quantumValidation } from "../api/client";
import BoxPlot from "../components/BoxPlot";
import GapBars from "../components/charts/GapBars";
import { Empty, ErrorState, Loading, MockBadge, QueryState } from "../components/States";
import StatsTable from "../components/StatsTable";
import { Hi, InsightBlock, InsightsColumn } from "../components/ui/Insights";
import { Checkbox, Chip, DataTable, KpiCard, Panel, Segmented } from "../components/ui/primitives";
import { PageShell, SubNav, type SubNavItem } from "../components/ui/Shell";
import { algoKeyOf, bestByInstance, headToHead, optimumHits, pKeyFor, referenceOf } from "../lib/benchStats";
import { algoColor } from "../lib/colors";
import { useDemoMode } from "../lib/demoMode";
import { fmt } from "../lib/format";
import { algoLabel } from "../lib/labels";
import { benchmarkKeys, computeVerdict } from "../lib/verdict";

type Row = Record<string, unknown>;
type Section = "headline" | "ablation" | "scaling" | "milp" | "qubo" | "figures";

// Which exported tables each sub-nav section shows (first available is the default).
const TABLES: Record<Exclude<Section, "qubo" | "figures">, string[]> = {
  headline: ["confirm_d54", "bench_core_v1"],
  ablation: ["ablation", "ablation_evals", "alpha_sweep"],
  scaling: ["scaling_v2"],
  milp: ["p_small"],
};

const NOT_CLAIMED = [
  "No quantum speedup or quantum advantage: QPSO is a classical, quantum-inspired algorithm; the QUBO slot runs on a classical simulated annealer.",
  "No optimality guarantee: these are heuristics; gaps are measured against best-known solutions.",
  "The QUBO slot is slower than 2-opt on classical hardware and does not help the search under a time budget.",
  "OR-Tools (industry reference) is ahead on CMT1 and on the largest scaling instances.",
  "Traffic and incidents are simulated; CO₂ is an illustrative model; the fleet scale factor S is a modelling assumption.",
];

function FigureImg({ src }: { src: string }) {
  const [failed, setFailed] = useState(false);
  if (failed) return <div className="rounded-lg p-4 font-mono text-[11px] text-mute" style={{ border: "1px dashed var(--line-2)" }}>Figure unavailable: {src}</div>;
  return <img src={fileUrl(src)} alt={`Exported figure ${src}`} loading="lazy" className="w-full rounded-lg bg-white" onError={() => setFailed(true)} />;
}

function parseCsv(text: string): Row[] {
  const lines = text.trim().split(/\r?\n/);
  const split = (l: string) => {
    const out: string[] = [];
    let cur = "";
    let q = false;
    for (const ch of l) {
      if (ch === '"') q = !q;
      else if (ch === "," && !q) {
        out.push(cur);
        cur = "";
      } else cur += ch;
    }
    out.push(cur);
    return out;
  };
  const head = split(lines[0]);
  return lines.slice(1).map((l) => {
    const cells = split(l);
    const r: Row = {};
    head.forEach((h, i) => {
      const v = cells[i] ?? "";
      r[h] = v !== "" && Number.isFinite(Number(v)) ? Number(v) : v;
    });
    return r;
  });
}

const COMPACT_COLS = ["algorithm", "instance", "budget", "runs", "gap_mean_pct", "gap_std_pct", "gap_best_pct", "fleet_violations"];

export default function BenchmarkStudio() {
  const demo = useDemoMode();
  const list = useQuery({ queryKey: ["benchmarks"], queryFn: ({ signal }) => listBenchmarks({ signal }) });
  const items = useMemo(
    () => (list.data ?? []).map((x) => (typeof x === "string" ? { name: x, title: x } : { name: String(x.name), title: String(x.title ?? x.name) })),
    [list.data],
  );
  const available = useMemo(() => new Set(items.map((i) => i.name)), [items]);
  const [section, setSection] = useState<Section>("headline");
  const [pick, setPick] = useState<Record<string, string>>({});
  // Figures/QUBO keep showing the last table section's table (its figures).
  const [lastTable, setLastTable] = useState<keyof typeof TABLES>("headline");
  useEffect(() => {
    if (section in TABLES) setLastTable(section as keyof typeof TABLES);
  }, [section]);
  const tSection: keyof typeof TABLES = section in TABLES ? (section as keyof typeof TABLES) : lastTable;
  const tableOptions = TABLES[tSection].filter((n) => available.has(n));
  const name = pick[tSection] && tableOptions.includes(pick[tSection]) ? pick[tSection] : (tableOptions[0] ?? null);

  const bench = useQuery({
    queryKey: ["benchmark", name],
    queryFn: ({ signal }) => getBenchmark(name!, { signal }),
    enabled: !!name,
  });
  const qubo = useQuery({ queryKey: ["qubo-validation"], queryFn: ({ signal }) => quantumValidation({ signal }), enabled: section === "qubo" });
  const milpCsv = useQuery({
    queryKey: ["milp-csv"],
    queryFn: async ({ signal }) => {
      const res = await fetch(fileUrl("tables/milp_p_instances.csv"), { signal });
      if (!res.ok || (res.headers.get("content-type") ?? "").includes("text/html")) throw new Error("MILP table not available");
      return parseCsv(await res.text());
    },
    enabled: section === "milp" && !demo,
    retry: false,
  });

  const rows: Row[] = bench.data?.table ?? [];
  const keys = useMemo(() => benchmarkKeys(rows), [rows]);
  const aKey = useMemo(() => algoKeyOf(rows), [rows]);
  const instances = useMemo(() => (keys.instance ? Array.from(new Set(rows.map((r) => String(r[keys.instance!])))) : []), [rows, keys.instance]);
  const [inst, setInst] = useState<string>("__all");
  const [allCols, setAllCols] = useState(false);
  useEffect(() => setInst("__all"), [name]);
  const filtered = inst === "__all" || !keys.instance ? rows : rows.filter((r) => String(r[keys.instance!]) === inst);
  const verdict = useMemo(() => computeVerdict(filtered), [filtered]);
  const ref = useMemo(() => referenceOf(rows, bench.data?.meta), [rows, bench.data?.meta]);
  const h2h = useMemo(() => {
    const prio = (a: string) => (/ortools/.test(a) ? 0 : /^pso/.test(a) ? 1 : 2);
    return (ref ? headToHead(rows, ref) : []).sort((a, b) => prio(a.other) - prio(b.other));
  }, [rows, ref]);
  const best = useMemo(() => bestByInstance(rows), [rows]);
  const refBest = ref ? Array.from(best.values()).filter((a) => a.includes(ref)).length : 0;
  const pKey = ref ? pKeyFor(rows, ref) : null;

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
          .map((r) => ({ label: algoLabel(String(r[keys.algorithm!])), values: (r[arrayKey] as number[]) ?? [], color: algoColor(String(r[keys.algorithm!])) }))
      : [];

  const bestRows = useMemo(() => {
    const s = new Set<Row>();
    if (!keys.algorithm || !keys.instance) return s;
    filtered.forEach((r) => {
      if (aKey && best.get(String(r[keys.instance!]))?.includes(String(r[aKey]))) s.add(r);
    });
    return s;
  }, [filtered, best, keys, aKey]);

  const cols = useMemo(() => {
    if (!filtered.length) return undefined;
    const present = Object.keys(filtered[0]).filter((k) => k !== arrayKey);
    if (allCols) return keys.algorithm ? [keys.algorithm, ...present.filter((k) => k !== keys.algorithm)] : present;
    return [...COMPACT_COLS.filter((c) => present.includes(c)), ...(pKey && present.includes(pKey) ? [pKey] : [])];
  }, [filtered, allCols, keys.algorithm, arrayKey, pKey]);

  const title = items.find((i) => i.name === name)?.title;
  const subItems: Array<SubNavItem<Section>> = [
    { id: "headline", label: "Headline", icon: BarChart3 },
    { id: "ablation", label: "Ablation", icon: Layers },
    { id: "scaling", label: "Scaling", icon: TrendingUp },
    { id: "milp", label: "vs MILP", icon: Scale },
    { id: "qubo", label: "QUBO", icon: Atom },
    { id: "figures", label: "Figures", icon: FlaskConical, count: bench.data?.figures?.length || null },
  ];

  const eyebrow = (() => {
    const m = bench.data?.meta;
    if (section === "qubo") return `QUBO VALIDATION · ${qubo.data?.table?.length ?? "–"} ROWS · SAMPLER VS BRUTE FORCE VS 2-OPT`;
    if (!m || !name) return "BENCHMARK STUDIO";
    return [name.toUpperCase(), m.runs != null ? `${m.runs} RUNS` : null, m.budget != null ? `BUDGET ${String(m.budget).toUpperCase()}` : null, pKey ? "HOLM-CORRECTED" : null].filter(Boolean).join(" · ");
  })();

  // ------------------------------------------------------------------ main panels
  const benchBody =
    list.isLoading ? (
      <Loading label="Loading benchmark list…" />
    ) : list.isError ? (
      <ErrorState error={list.error} onRetry={() => list.refetch()} />
    ) : !name ? (
      <Empty title="No benchmark table exported for this section" />
    ) : bench.isLoading ? (
      <Loading label="Loading benchmark…" />
    ) : bench.isError ? (
      <ErrorState error={bench.error} onRetry={() => bench.refetch()} />
    ) : rows.length === 0 ? (
      <Empty title="This benchmark table is empty" />
    ) : (
      <div className="space-y-3">
        {ref && h2h.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <KpiCard
              label={`Lowest mean gap (incl. ties) · ${algoLabel(ref)}`}
              value={`${refBest}/${best.size}`}
              unit="instances"
              tone="teal"
              context="computed from this table"
            />
            {h2h.slice(0, 2).map((h) => (
              <KpiCard
                key={h.other}
                label={`vs ${algoLabel(h.other)}`}
                value={h.wins}
                unit={`win${h.wins === 1 ? "" : "s"}`}
                delta={{ text: `${h.ties} tie${h.ties === 1 ? "" : "s"} · ${h.losses} loss${h.losses === 1 ? "" : "es"}`, tone: h.losses > 0 ? "amber" : "plain" }}
                context={`of ${h.instances} · Holm p < 0.05`}
              />
            ))}
          </div>
        )}
        {keys.instance && (aKey ?? keys.algorithm) && keys.gap && (
          <Panel
            title={keys.gap === "gap_mean_pct" ? "Mean gap to best-known (%)" : keys.gap.replace(/_/g, " ")}
            chips={<Chip>lower is better</Chip>}
            meta={title}
            bodyClassName="px-2 pb-3"
          >
            <GapBars rows={rows} instanceKey={keys.instance} algoKey={(aKey ?? keys.algorithm)!} gapKey={keys.gap} best={best} height={260} />
            <div className="flex flex-wrap gap-1.5 px-2 pt-1">
              {Array.from(best.entries()).map(([i, a]) => (
                <Chip key={i} tone={ref && a.includes(ref) ? "teal" : "plain"}>
                  {i} · best {a.map((x) => algoLabel(x)).join(" = ")}
                </Chip>
              ))}
            </div>
          </Panel>
        )}
        {section === "milp" && (
          <Panel title="Proven optimum reached (runs with gap 0)" chips={<Chip>from per-run gaps</Chip>} bodyClassName="px-4 pb-4 space-y-3">
            <DataTable>
              <thead>
                <tr>
                  <th>Instance</th>
                  <th>Algorithm</th>
                  <th>Optimum reached</th>
                  <th>Median time to optimum (s)</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => {
                  const h = optimumHits(r);
                  return (
                    <tr key={i}>
                      <td className="n">{String(r.instance)}</td>
                      <td>
                        <span className="mr-2 inline-block h-2 w-2 rounded-full" style={{ background: algoColor(String(r.algo)) }} />
                        {algoLabel(String(r.algo))}
                      </td>
                      <td className="n" style={{ color: h && h.hits === h.runs ? "var(--lime)" : undefined }}>
                        {h ? `${h.hits}/${h.runs}` : "–"}
                      </td>
                      <td className="n">{fmt(r.time_to_1pct_s_median, 3)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </DataTable>
            <div className="text-[11.5px] text-mute">Time column = median time to within 1% of the optimum, as exported.</div>
            <div className="micro pt-1">MILP (CBC) on the same instances</div>
            {demo ? (
              <div className="text-[12px] text-mute">The MILP table (results/tables/milp_p_instances.csv) is read through the API in live mode; it is not part of the offline demo export.</div>
            ) : milpCsv.isLoading ? (
              <Loading label="Loading MILP table…" />
            ) : milpCsv.isError ? (
              <div className="text-[12px] text-mute">MILP table unavailable: {String((milpCsv.error as Error).message)}</div>
            ) : milpCsv.data ? (
              <StatsTable rows={milpCsv.data} columns={["instance", "proven_optimum_sol", "verdict", "best_value", "gap_pct", "wall_s", "time_limit_s"].filter((c) => c in (milpCsv.data[0] ?? {}))} />
            ) : null}
          </Panel>
        )}
        <Panel
          title="Table"
          chips={
            keys.instance ? (
              <Segmented
                ariaLabel="Instance filter"
                size="sm"
                value={inst}
                onChange={setInst}
                options={[["__all", "All"] as [string, string], ...instances.map((i) => [i, i] as [string, string])]}
              />
            ) : undefined
          }
          meta={
            <span>
              Runs <span className="text-txt">{fmt(bench.data?.meta?.runs)}</span> · Budget <span className="text-txt">{fmt(bench.data?.meta?.budget)}</span>
            </span>
          }
          bodyClassName="px-4 pb-3"
        >
          <StatsTable
            rows={filtered}
            columns={cols}
            highlight={(r) => bestRows.has(r)}
            colorFor={(r) => (keys.algorithm ? algoColor(String(r[keys.algorithm])) : undefined)}
            labelFor={(c) => (c === pKey ? "Holm-corrected Wilcoxon p" : c.replace(/_/g, " "))}
          />
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <Checkbox checked={allCols} onChange={setAllCols}>
              Show all columns
            </Checkbox>
            <span className="font-mono text-[10px] text-lbl">best = lowest {keys.gap?.replace(/_/g, " ") ?? "value"} per instance{pKey ? ` · p = Holm-corrected Wilcoxon vs ${algoLabel(ref)}` : ""}</span>
          </div>
        </Panel>
        {boxGroups.length > 0 && (
          <Panel title={`Per-run distribution${boxInstance ? ` · ${boxInstance}` : ""}`} chips={<Chip>{arrayKey}</Chip>} bodyClassName="px-4 pb-4">
            <BoxPlot groups={boxGroups} unit={arrayKey ?? ""} />
          </Panel>
        )}
      </div>
    );

  let main;
  if (section === "qubo") {
    main = (
      <QueryState q={qubo} isEmpty={(d) => !d?.table?.length} empty={<Empty title="No validation table yet">Run scripts/run_qubo_check.py.</Empty>}>
        {(d) => {
          const t = d.table;
          // KPI ranges over the CVRPLIB rows when present (single-route rows would widen them)
          const cv = t.filter((r) => /cvrplib/i.test(String(r.source ?? "")));
          const base = cv.length ? cv : t;
          const scope = cv.length ? "CVRPLIB routes" : "all rows";
          const nums = (k: string) => base.map((r) => r[k]).filter((v): v is number => typeof v === "number");
          const feas = nums("neal_feasible_pct");
          const opt = nums("neal_optimal_pct");
          const nealMs = nums("time_per_route_neal_ms");
          const twoMs = nums("time_per_route_2opt_ms");
          const range = (a: number[], digits = 0) => (a.length ? (Math.min(...a) === Math.max(...a) ? fmt(a[0], digits) : `${fmt(Math.min(...a), digits)}–${fmt(Math.max(...a), digits)}`) : "–");
          return (
            <div className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-3">
                <KpiCard label="Sampler feasible" value={range(feas)} unit="% of routes" tone="lime" context={`neal · ${scope}`} />
                <KpiCard label="Sampler optimal" value={range(opt)} unit="% of routes" context={`vs brute force · ${scope}`} />
                <KpiCard label="Time per route" value={range(nealMs)} unit="ms" tone="amber" context={`2-opt: ${range(twoMs, 3)} ms · ${scope}`} />
              </div>
              <Panel title="QUBO validation (sampler vs brute force vs 2-opt)" meta={<Link to="/quantum" className="text-teal underline">open Quantum lab →</Link>} bodyClassName="px-4 pb-3">
                <StatsTable rows={t} />
              </Panel>
            </div>
          );
        }}
      </QueryState>
    );
  } else if (section === "figures") {
    main =
      bench.data?.figures?.length ? (
        <div className="grid gap-3 md:grid-cols-2">
          {bench.data.figures.map((f) => (
            <Panel key={f} title={f.split("/").pop()} bodyClassName="p-2">
              <FigureImg src={f} />
            </Panel>
          ))}
        </div>
      ) : (
        <Empty title="No figures exported for this table">Pick a table under Headline, Ablation, Scaling or vs MILP first.</Empty>
      );
  } else {
    main = benchBody;
  }

  return (
    <PageShell
      hero={{
        eyebrow,
        title: "Measured fairly.",
        titleAccent: "Reported honestly.",
        lead: "Equal time budgets, the same seeds for every algorithm and Holm-corrected Wilcoxon tests. Verdicts and win counts are computed from the exported tables, including where QPSO does not win.",
        meta: title ? (
          <span className="flex items-center gap-2">
            table · {title} <MockBadge text={name} />
          </span>
        ) : undefined,
        actions: (
          <>
            {tableOptions.length > 1 && section !== "qubo" && (
              <Segmented ariaLabel="Benchmark table" size="sm" value={name ?? ""} onChange={(v) => setPick((p) => ({ ...p, [tSection]: v }))} options={tableOptions.map((n) => [n, n] as [string, string])} />
            )}
            <Link to="/convergence" className="btn-secondary">
              Convergence overlay →
            </Link>
          </>
        ),
      }}
      subnav={<SubNav title="Benchmarks" items={subItems} active={section} onChange={setSection} />}
      insights={
        <InsightsColumn>
          {section !== "qubo" && section !== "figures" && (
            <InsightBlock label="Verdict (computed from the table)" tone="teal">
              {bench.data && rows.length ? (
                <ul className="space-y-1.5">
                  {verdict.map((v, i) => (
                    <li key={i}>{v}</li>
                  ))}
                </ul>
              ) : (
                <span className="text-mute">No table loaded.</span>
              )}
            </InsightBlock>
          )}
          {section === "qubo" && (
            <InsightBlock label="Verdict" tone="amber">
              The sampler returns a <Hi tone="lime">feasible</Hi> order on every validated route, but it is <Hi tone="amber">slower than 2-opt</Hi> on classical
              hardware and not always optimal. We claim readiness, not advantage.
            </InsightBlock>
          )}
          {ref && h2h.length > 0 && section !== "qubo" && section !== "figures" && (
            <InsightBlock label={`Head-to-head · ${algoLabel(ref)}`}>
              <table className="w-full font-mono text-[11px]">
                <thead>
                  <tr className="text-left text-lbl">
                    <th className="pb-1 font-normal">vs</th>
                    <th className="pb-1 text-right font-normal">W</th>
                    <th className="pb-1 text-right font-normal">T</th>
                    <th className="pb-1 text-right font-normal">L</th>
                  </tr>
                </thead>
                <tbody>
                  {h2h.map((h) => (
                    <tr key={h.other}>
                      <td className="py-0.5 pr-2 font-sans text-[12px]">
                        <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full" style={{ background: algoColor(h.other) }} />
                        {algoLabel(h.other)}
                      </td>
                      <td className="text-right text-teal">{h.wins}</td>
                      <td className="text-right text-mute">{h.ties}</td>
                      <td className="text-right" style={{ color: h.losses ? "var(--amber)" : "var(--mute)" }}>
                        {h.losses}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="mt-1.5 text-[11px] text-lbl">Win/loss = Holm-corrected Wilcoxon p &lt; 0.05 and lower/higher mean gap; otherwise tie.</div>
            </InsightBlock>
          )}
          <InsightBlock label="What we do not claim" tone="amber">
            <ul className="space-y-1.5">
              {NOT_CLAIMED.map((c) => (
                <li key={c} className="flex gap-2">
                  <span className="mt-[7px] inline-block h-1 w-1 shrink-0 rounded-full bg-amber" />
                  {c}
                </li>
              ))}
            </ul>
          </InsightBlock>
          <div className="text-[11px] leading-relaxed text-lbl">
            Within each table every algorithm gets the same time budget and the same seeds; the metaheuristics share one decoder, while OR-Tools (industry
            reference) uses its own C++ model.
          </div>
        </InsightsColumn>
      }
    >
      <div key={`${section}-${name}`} className="qr-fade">
        {main}
      </div>
    </PageShell>
  );
}
