import { Panel } from "./ui/primitives";

export default function ExplanationPanel({ lines, title = "Why this plan" }: { lines: string[]; title?: string }) {
  return (
    <Panel title={title} meta="deterministic template sentences · no LLM" bodyClassName="px-4 pb-4">
      {lines.length === 0 ? (
        <div className="text-[13px] text-mute">No explanation sentences in this result.</div>
      ) : (
        <ul className="space-y-1.5 text-[13px] leading-relaxed text-txt2">
          {lines.map((l, i) => (
            <li key={i} className="flex gap-2">
              <span className="mt-[7px] inline-block h-1 w-1 shrink-0 rounded-full bg-teal" />
              {l}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
