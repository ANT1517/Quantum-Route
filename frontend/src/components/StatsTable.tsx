import { fmt } from "../lib/format";

type Row = Record<string, unknown>;

export function tableColumns(rows: Row[]): string[] {
  const set = new Set<string>();
  rows.forEach((r) => Object.keys(r).forEach((k) => set.add(k)));
  return Array.from(set);
}

/** Generic table: columns are the union of row keys (first-seen order) unless given. */
export default function StatsTable({
  rows,
  columns,
  highlight,
  colorFor,
}: {
  rows: Row[];
  columns?: string[];
  highlight?: (row: Row) => boolean;
  colorFor?: (row: Row) => string | undefined;
}) {
  if (!rows.length) return <div className="text-sm text-slate-500">Table is empty.</div>;
  const cols = columns ?? tableColumns(rows);
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs uppercase text-slate-500">
            {cols.map((c) => (
              <th key={c} className="whitespace-nowrap py-2 pr-4">
                {c.replace(/_/g, " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const col = colorFor?.(r);
            return (
              <tr key={i} className={`border-b border-slate-100 ${highlight?.(r) ? "bg-teal-50 font-semibold" : ""}`}>
                {cols.map((c, j) => (
                  <td key={c} className={`whitespace-nowrap py-1.5 pr-4 ${typeof r[c] === "number" ? "tabular-nums" : ""}`}>
                    {j === 0 && col && <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full align-middle" style={{ background: col }} />}
                    {fmt(r[c], 3)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
