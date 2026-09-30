import type { ReactNode } from "react";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 p-4 text-sm text-slate-500" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-teal-600 border-t-transparent" />
      {label}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const msg = error instanceof Error ? error.message : String(error ?? "Unknown error");
  return (
    <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
      <div className="font-semibold">Something went wrong</div>
      <div className="mt-1">{msg}</div>
      {onRetry && (
        <button className="btn-secondary mt-2" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
      <div className="font-semibold text-slate-700">{title}</div>
      {children && <div className="mt-2">{children}</div>}
    </div>
  );
}

interface QueryLike<T> {
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  data: T | undefined;
  refetch: () => unknown;
}

/** Render loading / error / empty / success from a react-query result. */
export function QueryState<T>({
  q,
  isEmpty,
  empty,
  children,
  loadingLabel,
}: {
  q: QueryLike<T>;
  isEmpty?: (d: T) => boolean;
  empty?: ReactNode;
  loadingLabel?: string;
  children: (d: T) => ReactNode;
}) {
  if (q.isLoading) return <Loading label={loadingLabel} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  if (q.data === undefined || (isEmpty && isEmpty(q.data))) return <>{empty ?? <Empty title="No data" />}</>;
  return <>{children(q.data)}</>;
}

/** Shown whenever an id/label contains "MOCK" so placeholder data is never mistaken for results. */
export function MockBadge({ text }: { text?: string | null }) {
  if (!text || !/mock/i.test(text)) return null;
  return (
    <span className="badge bg-fuchsia-100 text-fuchsia-800" title="Placeholder data, not a real result">
      MOCK DATA
    </span>
  );
}
