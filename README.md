# QuantumRoute

Quantum-inspired (QPSO) fleet routing on congestion-aware road graphs, with a fair benchmark studio.
SIH 2026 · PS 26137 · Egreen Quanta. Single source of truth: [`QUANTUMROUTE_MASTER_DOC.md`](QUANTUMROUTE_MASTER_DOC.md).

## Honesty statement
QPSO is a classical algorithm inspired by quantum mechanics; it runs on ordinary CPUs. The QUBO slot
uses a classical sampler today. Traffic is simulated. No quantum speedup is claimed. The platform scale
factor S used in the fleet-impact demo is a modelling assumption.

## What it does
Hyderabad road graph + BPR traffic · QPSO (Split decoding, local search, tunneling) · PSO/GA/SA/OR-Tools/
MILP/Held-Karp baselines · system-optimal fleet routing · incident re-routing · shortest path ·
QUBO sub-route slot · benchmark studio with seeds and statistics.

Default engine: **QPSO-noQUBO (tuned)** — QPSO with the QUBO slot off and fixed α = 0.3, tuned on CVRPLIB
tuning instances only (D59). Google OR-Tools is selectable as the industry reference engine.
Results and what we can and cannot claim: [`results/RESULTS_SUMMARY.md`](results/RESULTS_SUMMARY.md).

## Quick start
```bash
python -m venv .venv && .venv/Scripts/activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt && pip install -e engine
python scripts/build_hyd.py            # uses cached data/hyd/roadnet.npz; builds TD matrices (~45 s once)
pytest -q                              # contract, engine, traffic, fleet tests
uvicorn backend.app.main:app --port 8000
cd frontend && npm install && npm run dev      # http://localhost:5173
# Offline demo (no backend, no network): npm run dev:demo   (or VITE_DEMO_MODE=true npm run dev)
```
Python 3.11+ (3.13 tested). PuLP must be 2.x.

## Running experiments and demos
**Every experiment and demo run goes through the standalone runner in its own console window** — see
[`docs/RUNNING_EXPERIMENTS.md`](docs/RUNNING_EXPERIMENTS.md) (rule D57: background-launched processes were
throttled to ≈2.3–2.5× less CPU, which made time-budget comparisons unfair).
```powershell
Start-Process -FilePath .venv\Scripts\python.exe -ArgumentList "scripts/runner.py --phase demos" -WindowStyle Minimized
```
Phase `demos`: Hyderabad 17:30 vs 03:00 plans, fleet impact (naive / user_eq / system_opt), incident
re-routing, ambulance shortest path (`run_fleet_demo.py`), demo figures, then the demo-mode export
(`export_api_json.py`, `export_demo.py` → `frontend/public/demo/`). Each output records which engine
produced it (`algorithm` field). Benchmark phases and their configs are listed in `scripts/runner.py` and
`configs/experiments/`. Every quotable number is in `results/SLIDE_NUMBERS.md`; never copy numbers by hand.

## Architecture
React (Vite, Leaflet, Recharts) → FastAPI (REST + WebSocket) → QuantumFlux engine (`engine/qflux`) →
SQLite + `results/`. The engine is a standalone package; every figure can be regenerated from `scripts/`.

| Folder | Contents |
|---|---|
| `engine/qflux/core`, `algos`, `quantum`, `bench` | Split, evaluator, local search, QPSO + baselines, QUBO slot, benchmark harness |
| `engine/qflux/traffic`, `sp`, `dynamic`, `explain` | Road graphs, time-dependent matrices, fleet equilibrium, incidents, shortest path, explanations |
| `engine/qflux/api.py` | Entry points used by the backend (`build_instance`, `run_job`, `fleet_compare`, …) |
| `backend/` | FastAPI app, job manager, SQLite |
| `frontend/` | React screens; `public/demo/` holds exported demo JSON |
| `data/` | CVRPLIB instances, Hyderabad road network cache, customers |

## Team
[Member 1] … [Member 6]

## Limitations and future scope
Simulated traffic; heuristic (no optimality guarantee); illustrative CO₂ curve; the fleet-impact effect
depends on the scale factor S; see §19 of the master doc.
