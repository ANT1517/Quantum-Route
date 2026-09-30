import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  resetKey?: string;
}
interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    (window as unknown as { __qrLastError?: unknown }).__qrLastError = { error, info };
  }

  componentDidUpdate(prev: Props) {
    if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null });
  }

  render() {
    if (this.state.error) {
      return (
        <div className="m-4 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
          <div className="font-semibold">This screen crashed.</div>
          <div className="mt-1 font-mono text-xs">{this.state.error.message}</div>
          <button className="btn-secondary mt-2" onClick={() => this.setState({ error: null })}>
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
