import { Outlet, useLocation } from "react-router-dom";
import ErrorBoundary from "./ErrorBoundary";
import Toasts from "./Toasts";
import { GlobalSvgDefs } from "./charts/theme";
import { TopNav } from "./ui/Shell";

export default function Layout() {
  const loc = useLocation();
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#qr-main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[3000] focus:rounded-md focus:bg-white focus:px-3 focus:py-2 focus:text-black">
        Skip to content
      </a>
      <GlobalSvgDefs />
      <TopNav />
      <main id="qr-main" className="mx-auto w-full max-w-[1480px] flex-1 px-4 lg:px-6">
        <ErrorBoundary resetKey={loc.pathname}>
          <Outlet />
        </ErrorBoundary>
      </main>
      <footer className="px-4 pb-5 text-center font-mono text-[10.5px] text-lbl">
        QPSO is a classical, quantum-inspired metaheuristic running on ordinary CPUs. No quantum speedup is claimed. Traffic is simulated.
      </footer>
      <Toasts />
    </div>
  );
}
