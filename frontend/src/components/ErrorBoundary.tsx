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
        <div className="m-4 rounded-xl p-4 text-[13px]" role="alert" style={{ background: "rgba(255,122,122,.05)", border: "1px solid rgba(255,122,122,.3)" }}>
          <div className="font-semibold text-danger">This screen crashed.</div>
          <div className="mt-1 font-mono text-[11px] text-txt2">{this.state.error.message}</div>
          <button type="button" className="btn-secondary btn-sm mt-3" onClick={() => this.setState({ error: null })}>
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
