export type ToastKind = "error" | "info" | "success";
export interface Toast { id: number; kind: ToastKind; message: string }

type Listener = (toasts: Toast[]) => void;
let toasts: Toast[] = [];
let nextId = 1;
const listeners = new Set<Listener>();

function emit() {
  listeners.forEach((l) => l(toasts));
}

export function notify(message: string, kind: ToastKind = "error", ttlMs = 5000) {
  const id = nextId++;
  // de-duplicate identical visible messages
  if (toasts.some((t) => t.message === message && t.kind === kind)) return;
  toasts = [...toasts, { id, kind, message }];
  emit();
  setTimeout(() => dismiss(id), ttlMs);
}

export function dismiss(id: number) {
  toasts = toasts.filter((t) => t.id !== id);
  emit();
}

export function subscribeToasts(l: Listener): () => void {
  listeners.add(l);
  l(toasts);
  return () => {
    listeners.delete(l);
  };
}
