export default function ExplanationPanel({ lines, title = "Why this plan" }: { lines: string[]; title?: string }) {
  return (
    <div className="card">
      <div className="label">{title}</div>
      {lines.length === 0 ? (
        <div className="text-sm text-slate-500">No explanation sentences in this result.</div>
      ) : (
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
          {lines.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      )}
      <div className="mt-2 text-xs text-slate-400">Deterministic template sentences generated from the result (no LLM).</div>
    </div>
  );
}
