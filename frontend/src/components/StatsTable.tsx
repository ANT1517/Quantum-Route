import { fmt } from "../lib/format";
import { DataTable } from "./ui/primitives";

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
  labelFor,
}: {
  rows: Row[];
  columns?: string[];
  highlight?: (row: Row) => boolean;
  colorFor?: (row: Row) => string | undefined;
  labelFor?: (col: string) => string;
}) {
  if (!rows.length) return <div className="text-[13px] text-mute">Table is empty.</div>;
  const cols = columns ?? tableColumns(rows);
  return (
    <DataTable>
      <thead>
        <tr>
          {cols.map((c) => (
            <th key={c}>{labelFor ? labelFor(c) : c.replace(/_/g, " ")}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => {
          const col = colorFor?.(r);
          const hi = highlight?.(r);
          return (
            <tr key={i} style={hi ? { background: "rgba(79,227,209,.05)" } : undefined}>
              {cols.map((c, j) => (
                <td key={c} className={typeof r[c] === "number" ? "n" : ""} style={hi ? { color: "var(--txt)" } : undefined}>
                  {j === 0 && col && <span className="mr-2 inline-block h-2 w-2 rounded-full align-middle" style={{ background: col, boxShadow: hi ? `0 0 8px ${col}` : undefined }} />}
                  {fmt(r[c], 3)}
                  {j === 0 && hi && <span className="chip chip-teal ml-2">best</span>}
                </td>
              ))}
            </tr>
          );
        })}
      </tbody>
    </DataTable>
  );
}
