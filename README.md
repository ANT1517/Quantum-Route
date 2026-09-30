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

## Demo data
```bash
python scripts/run_fleet_demo.py      # Hyderabad: 17:30 vs 03:00 plans, fleet impact, incident, ambulance
python scripts/plot_demo.py           # results/demo/fig_fleet_impact.png, fig_time_of_day.png
python scripts/export_demo.py         # copies real results into frontend/public/demo/ for demo mode
```
Each output file records which planner produced it (`algorithm` field).

## Reproduce figures
```bash
python scripts/run_bench.py --exp bench_core
python scripts/run_ablation.py
python scripts/run_alpha_sweep.py
python scripts/run_scaling.py
python scripts/run_fleet_demo.py
python scripts/run_qubo_check.py
```
Headline numbers are traceable in `results/SLIDE_NUMBERS.md`; never copy numbers by hand.

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
