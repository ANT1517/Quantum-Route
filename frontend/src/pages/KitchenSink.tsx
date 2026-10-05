// Dev-only component gallery (/dev/kitchen-sink). Not linked from the nav; not registered in production builds.
// Sample values below are placeholders for visual QA only and never reach a real screen.
import { BarChart3, Layers, Map as MapIcon } from "lucide-react";
import { useState } from "react";
import ConvergenceChart from "../components/ConvergenceChart";
import CongestionChart, { CongestionLegend } from "../components/charts/CongestionChart";
import { Empty, ErrorState, Loading } from "../components/States";
import { DecisionLog, Hi, InsightBlock, InsightsColumn, SignalRow } from "../components/ui/Insights";
import { Checkbox, Chip, DataTable, InfoTip, KpiCard, Panel, Segmented, Select, Skeleton, Slider } from "../components/ui/primitives";
import { PageShell, SubNav } from "../components/ui/Shell";
import { notify } from "../lib/toast";

const SAMPLE = Array.from({ length: 40 }, (_, i) => ({ iter: i, evals: i * 100, best_F: 1 / (1 + i * 0.15) + 0.5 }));

export default function KitchenSink() {
  const [seg, setSeg] = useState("a");
  const [v, setV] = useState(0.4);
  const [c, setC] = useState(true);
  const [s, setS] = useState<"one" | "two" | "three">("one");
  return (
    <PageShell
      hero={{
        eyebrow: "DEV · KITCHEN SINK · PLACEHOLDER VALUES",
        title: "Every component,",
        titleAccent: "one page.",
        lead: "Visual QA for the v3 design system. Values here are placeholders.",
        actions: (
          <>
            <button type="button" className="btn-ghost">
              Ghost
            </button>
            <button type="button" className="btn-secondary">
              Secondary
            </button>
            <button type="button" className="btn-warn">
              + Warn
            </button>
            <button type="button" className="btn-primary" onClick={() => notify("Toast example", "success")}>
              Primary →
            </button>
          </>
        ),
        meta: "meta line · mono",
      }}
      subnav={
        <SubNav
          title="Kitchen sink"
          active={s}
          onChange={setS}
          items={[
            { id: "one", label: "Controls", icon: Layers, count: 7 },
            { id: "two", label: "Charts", icon: BarChart3 },
            { id: "three", label: "States", icon: MapIcon, count: 2, countTone: "amber" },
          ]}
        />
      }
      insights={
        <InsightsColumn>
          <InsightBlock label="Recommended action" tone="teal">
            Highlight <Hi>teal</Hi> and <Hi tone="amber">amber</Hi> phrases.
          </InsightBlock>
          <InsightBlock label="Signal summary">
            <SignalRow k="Row" v="1.00" tone="teal" />
            <SignalRow k="Row" v="2.00" />
          </InsightBlock>
          <DecisionLog lines={[{ t: "00:00", text: "placeholder line" }]} />
        </InsightsColumn>
      }
    >
      <div className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-3">
          <KpiCard label="Label" value="123.4" unit="min" delta={{ text: "−1.0 min", tone: "lime" }} context="context" />
          <KpiCard label="Amber" value="45.6" unit="min" tone="amber" />
          <KpiCard label="Feasibility" value="Feasible" tone="lime" />
        </div>
        <Panel title="Controls" chips={<Chip tone="teal">chip</Chip>} meta="meta" bodyClassName="px-4 pb-4 space-y-3">
          <div className="flex flex-wrap gap-1.5">
            <Chip>plain</Chip>
            <Chip tone="teal">teal</Chip>
            <Chip tone="lime">lime</Chip>
            <Chip tone="amber">amber</Chip>
            <Chip tone="red">red</Chip>
            <Chip tone="violet">violet</Chip>
          </div>
          <Segmented ariaLabel="Example" value={seg} onChange={setSeg} options={[["a", "Alpha"], ["b", "Beta"], ["c", "Gamma"]]} />
          <Slider ariaLabel="Example slider" min={0} max={1} step={0.01} value={v} onChange={setV} />
          <div className="flex items-center gap-2">
            <Checkbox checked={c} onChange={setC}>
              Checkbox
            </Checkbox>
            <InfoTip text="Tooltip text" />
          </div>
          <Select aria-label="Example select" defaultValue="1">
            <option value="1">Option 1</option>
            <option value="2">Option 2</option>
          </Select>
          <input className="input" placeholder="Input" aria-label="Example input" />
          <DataTable>
            <thead>
              <tr>
                <th>Col</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Row</td>
                <td className="n">1.234</td>
              </tr>
            </tbody>
          </DataTable>
        </Panel>
        <Panel title="Charts" meta={<CongestionLegend />} bodyClassName="px-2 pb-2">
          <CongestionChart departMin={1050} height={200} />
          <ConvergenceChart series={[{ name: "SAMPLE", color: "#4FE3D1", points: SAMPLE }]} height={200} />
        </Panel>
        <Loading />
        <Skeleton height={40} />
        <Empty title="Empty state">Body</Empty>
        <ErrorState error="Error state" onRetry={() => undefined} />
      </div>
    </PageShell>
  );
}
