import { Route, Routes } from "react-router-dom";
import ErrorBoundary from "./components/ErrorBoundary";
import Layout from "./components/Layout";
import { Empty } from "./components/States";
import BenchmarkStudio from "./pages/BenchmarkStudio";
import Convergence from "./pages/Convergence";
import FleetImpact from "./pages/FleetImpact";
import Home from "./pages/Home";
import QuantumLab from "./pages/QuantumLab";
import Results from "./pages/Results";
import RunOptimizer from "./pages/RunOptimizer";
import ScenarioBuilder from "./pages/ScenarioBuilder";
import ShortestPath from "./pages/ShortestPath";

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="scenario" element={<ScenarioBuilder />} />
          <Route path="run" element={<RunOptimizer />} />
          <Route path="results" element={<Results />} />
          <Route path="fleet" element={<FleetImpact />} />
          <Route path="path" element={<ShortestPath />} />
          <Route path="bench" element={<BenchmarkStudio />} />
          <Route path="convergence" element={<Convergence />} />
          <Route path="quantum" element={<QuantumLab />} />
          <Route path="*" element={<Empty title="Page not found" />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  );
}
