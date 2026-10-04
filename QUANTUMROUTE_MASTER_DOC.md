# QuantumRoute — Unified Master Document (Single Source of Truth)

**SIH 2026 · PS 26137 · Quantum-Inspired Intelligent Traffic Route Optimization in Transportation Systems Using Metaheuristic Optimization**
Organization: Egreen Quanta · Category: Software · Theme: Transportation & Logistics
Document version: **4.0 (unified)** — merges *QuantumFlux Master Doc v3* (engine, algorithms, experiments) and *QuantumRoute Master Blueprint v1.0* (product, API, UX, testing, demo). **Both source documents are now superseded.**

Naming: **QuantumRoute** is the platform (what judges see). **QuantumFlux** is its optimization engine (the Python package `qflux`).

---

## 0. Read Me First

### 0.1 Rules for humans and AI agents
1. **This document wins.** If code, chat, or an older doc disagrees with it, this doc is correct. If this doc is wrong, fix the doc first (bump §0.4 and add to the Decision Log §17), then change code.
2. **Work phase by phase** (§9). Each phase lists owner, files, contracts used, steps, tests, and acceptance criteria. Appendix A has a ready-to-paste agent prompt for every phase.
3. **Contracts in §5 are frozen** after Phase 0 (engine types, config, REST API, result JSON, DB tables). Changing one = update §5 + Decision Log + tell the team.
4. **No invented numbers.** Every number on a slide or in the UI must come from `results/` produced by our scripts, or from a citation verified via §18.2. Planned ≠ measured.
5. **Honesty rules** (§1.4) apply to code comments, README, UI copy, PPT and the spoken pitch.
6. **Labels used in this doc:** *Requirement* = from the PS. *Decision* = our design choice (logged in §17). *Assumption* = not specified by the PS; must be stated as such if shown to judges. *[VERIFY]* = must be checked before submission.

### 0.2 What to do in the first 60 minutes (execution kickoff)
1. Everyone reads §1, §2, §5 (15 min).
2. M1 creates the repo from §4.3 and commits §5 contracts as code stubs (Phase 0).
3. M3 **starts the Hyderabad OSM download immediately** (slow; §6.1).
4. M2 downloads CVRPLIB instances + `.sol` files (§11.1) into `data/instances/`.
5. M4 creates the FastAPI skeleton returning **mock results** that match §5.5 exactly.
6. M5 creates the React app against those mocks.
7. M6 opens the PPT template and the §18.2 verification list.
8. Agree: API contract (§5.4), result JSON (§5.5), engine entry point `run_job()` (§5.3). Then everyone works in parallel against stubs.

### 0.3 What was merged from where
| Area | Taken from QuantumFlux v3 | Taken from QuantumRoute v1.0 | Merge change |
|---|---|---|---|
| Problem variant | TD-CVRP, Hyderabad, time-of-day | Congestion delay as an explicit objective | Objective now has **4 terms**: time, distance, congestion delay, CO₂ (§3.4) |
| Decoder | Optimal Prins Split, Lamarckian write-back | Fleet-size penalty λ | Greedy split replaced by Prins Split; λ penalty kept for fleet limit K |
| QPSO | Rank mbest, Sobol, adaptive coefficient, tunneling, vectorized | Coefficient schedule 0.8→0.3 found in prototype | Default 1.0→0.5 (literature); 0.8→0.3 included in sweep; **no clipping** of keys |
| Symbols | β used for QPSO *and* BPR (clash) | α for QPSO | **α = QPSO contraction–expansion; a, b = BPR** |
| Baselines | PSO, GA, SA, OR-Tools, MILP, equal-evals + equal-time | Held-Karp, Dijkstra/A*, QPSO shortest path | All kept; Held-Karp for single-route optimum, MILP for small CVRP |
| Instances | CVRPLIB (A, P, CMT, X) + Hyderabad OSM | Synthetic scenario generator | Three sources: **CVRPLIB** (credibility), **Hyderabad** (demo), **SynthCity** (tests, scaling, offline fallback) |
| Traffic | Class-based load-ratio → BPR, FIFO interpolation | Zone congestion events (circle on map) | One traffic model; incidents can be **edge lists or zones** |
| Fleet congestion | Marginal-cost system-optimal loop, scale factor S | — | Kept (flagship differentiator) |
| Quantum | QUBO sub-route slot validated vs brute force | — | Kept; plus a "Quantum Lab" screen |
| Product | Streamlit dashboard | React + FastAPI + jobs + WebSocket + DB + demo mode | **React + FastAPI**; Streamlit dropped; auth/admin moved to P2 |
| Testing | Engine/traffic unit tests | T01–T24 API/UI/security/edge tests | Merged into one test table (§10) |
| Pitch | 6-slide SIH idea template | 5-min demo script, judge Q&A, what-can-go-wrong, checklist | All kept, merged (§12–§14, §18) |
| Evidence | — | Prototype run: untuned QPSO without local search lost to GA on 1 synthetic instance | Kept as **Finding F0** (§1.5): motivates Split + LS + fair tuning |

### 0.4 Version history
| Version | Change |
|---|---|
| QF 1.0 / 2.0 | Research reports |
| QF 3.0 | Engine master doc |
| QR 1.0 | Product blueprint |
| **4.0** | Unified doc. Fixes listed in §0.5 |
| 4.1 | (2026-10-04, Person A) Memetic LS rule, rank re-normalisation, deadline-aware budgets, core set without A-n44-k6, 10 runs + parallel rule, `RunRecord.meta` (D28–D32) |
| 4.8 | (2026-10-04) D53 default engine QPSO-noQUBO, D55 OR-Tools matrix API, D56 Holm + effect sizes + P-instance comparison |
| 4.7 | (2026-10-04, Person A) D46 TD proxy LS, D51 memory-pressure audit + standalone runner, D52 backend timeout / T25 / MILP / neal-import fixes |
| 4.6 | (2026-10-04, Person A) D49 pre-registered P-core check + shuffled order + per-run CPU calibration; D50 scaling budgets |
| 4.5 | (2026-10-04, Person A) D44 timing-fairness check (no restart; hybrid CPU recorded; per-run timestamps), D45 pre-registered QPSO-noQUBO row |
| 4.4 | (2026-10-04, Person A) Exact O(1)-delta LS for static instances (D41); D42 granular neighbourhoods not needed; budgets by size class (D43); invalid-run guard for machine sleep |
| 4.3 | (2026-10-04, Person A) Time budget only for LS hybrids (D39); 30 runs + wall-time curves `RunRecord.meta["curve_t"]` (D40); fleet-infeasible runs excluded from gaps (D38 addendum) |
| 4.2 | (2026-10-04, Person A) Memetic trigger = LS on the best 25% of new positions (D33), RR+LS control (D34), A-n69-k9 tuning-only (D35), new bench_core gate (D36), `RunRecord.meta` logged as a frozen-file change (D37), T11 against proven optima, fleet limit K = k for Augerat A/P (D38) |

### 0.5 Fixes applied during the merge
| # | Problem | Fix |
|---|---|---|
| U1 | QuantumRoute decoder started a new route greedily when capacity overflowed — valid but far from optimal | Prins Split (optimal partition of a giant tour) |
| U2 | QuantumRoute QPSO clipped keys to [0,1] → many keys stick at 0 or 1 → ties → arbitrary orders | No clipping; only order matters |
| U3 | QuantumRoute QPSO evaluated particles in a pure-Python loop | Numba Split + vectorized update |
| U4 | QuantumRoute benchmarked only on self-generated instances | CVRPLIB with best-known solutions is the primary benchmark |
| U5 | Held-Karp gives single-vehicle optimum only; "enumerate splits" for multi-vehicle exact was unspecified | MILP (PuLP/CBC) for small CVRP; Held-Karp for single routes |
| U6 | β symbol clash (QPSO vs BPR) in QuantumFlux | α for QPSO, (a, b) for BPR |
| U7 | QuantumFlux had no metaheuristic for the shortest-path objective (O1 asks for both) | QPSO shortest path (priority encoding) benchmarked vs Dijkstra (§7.11) |
| U8 | QuantumFlux had CO₂ but no explicit congestion term, although the PS names congestion | Congestion delay term C added (§3.4) |
| U9 | Login/JWT/admin/audit consumed ~10 person-hours with little judging value | Guest-only in P0; auth is P2 |
| U10 | Streamlit vs React conflict | React + FastAPI; frontend **demo mode** replaces Streamlit's offline role |
| U11 | Hackathon/Delivery Table unknown in QuantumRoute | SIH idea stage: PPT is the primary deliverable; prototype + video strengthen it |

---

## 1. Executive Summary

### 1.1 One-liner
**QuantumRoute plans delivery-fleet routes on Hyderabad's real road network with a quantum-inspired swarm optimizer (QPSO), routes the fleet so it does not create its own traffic jams, minimizes time, distance, congestion and CO₂, re-plans when traffic changes, has a quantum-ready solver slot built into the pipeline — and proves every claim in a fair, reproducible Benchmark Studio.**

### 1.2 The 30-second explanation (for anyone)
Delivery vans waste time and fuel because choosing the best set of routes is mathematically very hard (NP-hard), and traffic keeps changing the answer. QuantumRoute models the city as a road graph whose travel times depend on congestion, then uses a search algorithm borrowed from quantum physics mathematics (it runs on ordinary computers) to find good routes for many vehicles at once. It races QPSO against classical methods on the same problems, shows routes on a map, plots how fast each method improves, and shows how the fleet's own traffic can be spread out to reduce congestion. The benefit is **measured, not assumed**.

### 1.3 What we deliver (idea stage, ~24 h)
1. **Engine (QuantumFlux):** QPSO for Time-Dependent CVRP with feasible-by-construction decoding, local search, tunneling escape, QUBO sub-route slot.
2. **Benchmark evidence:** CVRPLIB (Augerat A/P, CMT, Uchoa X) vs PSO, GA, SA, OR-Tools, MILP; equal evaluation and equal time budgets; multiple seeds; Wilcoxon tests; convergence, ablation, α-sensitivity, scaling to n = 1,000.
3. **Hyderabad demos:** time-of-day routing, naive vs system-optimal fleet routing, incident re-routing, ambulance shortest path, CO₂ vs time trade-off.
4. **Platform:** React + FastAPI web app (Scenario Builder, Run Optimizer with live convergence, Results map, Fleet Impact, Benchmark Studio, Quantum Lab, Shortest Path), with offline **demo mode**.
5. **SIH PPT (6 slides) + 2–3 min demo video + README.**

### 1.4 Honesty rules (non-negotiable)
- QPSO is a **classical** algorithm inspired by quantum-mechanical mathematics. It runs on ordinary CPUs. **No quantum speedup is claimed.**
- The QUBO slot runs a **classical simulated annealer** today. We claim **readiness**, measured by optimality rate vs brute force, not advantage.
- Traffic is **simulated** (load-ratio profiles + BPR). Say so.
- The platform scale factor S (§6.5.3) is a modelling assumption. Say so.
- We never write "first", "best", "guaranteed optimal". Heuristics give good solutions, not proofs.
- If QPSO does not win on some instance, we show it and explain where it helps and where it does not.

Safe wording for slides and speech:
> "QuantumRoute uses Quantum-behaved PSO, a classical metaheuristic whose particles sample new positions from a probability distribution derived from a quantum delta-potential-well model. It has a single main control parameter and a known convergence analysis. It runs on ordinary hardware. Our QUBO sub-route slot currently uses a classical sampler and can be pointed at a quantum annealer without redesign."

### 1.5 Evidence we already have (Finding F0)
Teammate prototype (≈80 lines NumPy): 1 synthetic instance, 30 customers, greedy split, raw weights, no local search, 6,000 evaluations, 5 seeds. Mean final cost: **GA 832.7, QPSO (α 0.8→0.3) 922.8, PSO 981.3**. QPSO with α 1.0→0.5 gave 1043.5.
**What it means:** (a) the pipeline works; (b) results are sensitive to α; (c) plain QPSO without a good decoder and local search does not automatically win. This is why the unified design uses Prins Split, Lamarckian local search, equal budgets, and ablations. **Do not quote F0 as a benchmark** — it is one untuned instance.

---

## 2. Problem, Users, Requirements

### 2.1 Plain terms
A logistics operator has a depot and K vans of capacity Q. Customers across Hyderabad have demands. We decide **which van serves which customers and in what order**, minimizing travel time, distance, congestion and emissions, under traffic that changes with time of day and incidents. We also solve the single-vehicle **shortest-path** problem (e.g., an ambulance). VRP is NP-hard, so we use QPSO and prove its quality against classical metaheuristics and exact methods.

### 2.2 Problem variant (Decision D1)
**Time-Dependent Capacitated VRP (TD-CVRP):** single depot, homogeneous fleet (K vans, capacity Q), static demands dᵢ, service time sᵢ, all vans leave at τ₀, travel time depends on departure time. Time windows are P1/finale.

### 2.3 Unified requirements (IDs used everywhere)
| ID | Requirement | Source | Priority |
|---|---|---|---|
| REQ-01 | Weighted graph network model | PS (E1) | Must |
| REQ-02 | Mathematical formulation | PS (E2) | Must |
| REQ-03 | Quantum-inspired metaheuristic (QPSO focus) | PS | Must |
| REQ-04 | Large-scale VRP | PS (O1) | Must |
| REQ-05 | Shortest-path problem | PS (O1) | Must |
| REQ-06 | Minimize time, distance, congestion | PS (O2) | Must |
| REQ-07 | Faster convergence / better quality / lower complexity vs classical | PS (O3) | Must |
| REQ-08 | Scalability for smart-city logistics | PS (O4) | Must |
| REQ-09 | Constraint handling | PS (E3) | Must |
| REQ-10 | Convergence analysis | PS (E4) | Must |
| REQ-11 | Systematic benchmarking | PS (E5) | Must |
| REQ-12 | Real-time or simulated traffic, dynamic route generation | PS | Must |
| REQ-13 | Benchmarked vs conventional metaheuristics | PS | Must |
| REQ-14 | Benchmarked vs exact methods | PS | Must |
| REQ-15 | Complete software platform | PS (Expected Solution) | Must |
| REQ-16 | Reproducibility (seeds, configs, equal budgets) | Hidden | Must |
| REQ-17 | Usable, explainable interface | Implicit | Must |
| REQ-18 | Real map data | Implicit | Should |
| REQ-19 | Quantum-hardware readiness (evaluator is a quantum company) | Implicit | Should |
| REQ-20 | Login / roles | Implicit | Nice (P2) |

### 2.4 Users and journeys (personas are illustrative — Assumption)
| Persona | Needs | Journey |
|---|---|---|
| Priya, logistics planner (primary) | Low-cost feasible plans, re-plan fast | J1: Scenario (Hyderabad, 60 customers, 6 vans, 17:30) → weights (time 50 / dist 20 / congestion 20 / CO₂ 10) → Run QPSO → live convergence → map + cost breakdown → export |
| Arjun, city traffic analyst | Fleet impact on congestion; what-if | J2: Add incident zone on map → re-optimize (warm start) → before/after delays; J5: Fleet Impact naive vs system-optimal |
| Dr. Meera, optimization researcher | Fair algorithm comparison | J3: Benchmark Studio → instances, algorithms, seeds, equal budget → table + p-values + convergence overlay → export |
| Ambulance dispatcher | Fastest path under live traffic | J6: Station → hospital at 17:30 → incident → recomputed path + ETA |
| Hackathon judge | Understand claims in minutes | J4: Open app (no login) → "Run demo" → map + convergence + benchmark verdict + Quantum Lab |

---

## 3. Mathematical Formulation (REQ-02)

### 3.1 Sets and parameters
- Road graph 𝒢 = (𝒩, ℰ). Each edge e: length ℓₑ, free-flow time t⁰ₑ, capacity Cₑ, road class κ(e).
- Customer graph G = (V, A), V = {0,…,n}, 0 = depot. Arc (i,j) is realized by a road path πᵢⱼ(τ) in 𝒢.
- dᵢ demand, sᵢ service time, Q capacity, K fleet size, τ₀ departure time.
- Leg quantities when departing i at time τ: tᵢⱼ(τ) travel time, t⁰ᵢⱼ free-flow time of the same path, Dᵢⱼ(τ) distance, Eᵢⱼ(τ) CO₂.

### 3.2 Reference MILP (static CVRP; exact baseline for n ≤ ~25)
Variables xᵢⱼ ∈ {0,1}, uᵢ ∈ ℝ (MTZ load).
```
min   Σ_{i∈V} Σ_{j∈V, j≠i} cᵢⱼ xᵢⱼ
s.t.  Σ_{i≠j} xᵢⱼ = 1                       ∀ j ∈ {1..n}        (enter once)
      Σ_{j≠i} xᵢⱼ = 1                       ∀ i ∈ {1..n}        (leave once)
      Σ_j x₀ⱼ = Σ_i xᵢ₀ ≤ K                                     (fleet)
      uᵢ − uⱼ + Q·xᵢⱼ ≤ Q − dⱼ              ∀ i≠j ∈ {1..n}      (MTZ + capacity)
      dᵢ ≤ uᵢ ≤ Q                           ∀ i ∈ {1..n}
```
With time dependence, cᵢⱼ becomes tᵢⱼ(start time), which is nonlinear — this is why exact methods are used only on static small instances.

### 3.3 Search-space formulation used by QuantumFlux
A solution is a **giant tour** σ (permutation of 1..n). `Split(σ)` (§7.3) returns the optimal partition of σ into capacity-feasible routes R = {r₁,…,r_m}.
Per route (0, c₁, …, c_k, 0), clock starts at τ₀:
```
a₀ = τ₀,   a_{p+1} = a_p + s_{c_p} + t_{c_p c_{p+1}}(a_p + s_{c_p})
```
Objective components (sums over all legs of all routes):
```
T(σ) = Σ t(·)                  total travel time
D(σ) = Σ D(·)                  total distance
C(σ) = Σ [t(·) − t⁰(·)]        total congestion delay (time above free flow)
E(σ) = Σ E(·)                  total CO₂
m(σ) = number of routes (vehicles used)
```

### 3.4 Fitness with FIXED reference normalization
```
F(σ) = w_T·T/T_ref + w_D·D/D_ref + w_C·C/C_ref + w_E·E/E_ref + λ·max(0, m − K),
w ≥ 0, w_T + w_D + w_C + w_E = 1
```
- References come from the **nearest-neighbour + Split** solution, computed **once** per instance and never changed. Population-relative normalization is forbidden (it makes pbest/gbest comparisons meaningless).
- `C_ref = max(C_nn, 0.05·T_nn)` so the congestion term never divides by ≈0 at night.
- λ = 0.5 (configurable). For CVRPLIB, w = (0, 1, 0, 0); K = k from the instance name for Augerat A/P (their published optima assume exactly k vehicles) and K = ∞ for CMT and Uchoa X (D38). Runs that exceed K are counted (`fleet_violations`) in every table.
- Hyderabad presets: **Balanced** (0.5, 0.2, 0.2, 0.1), **Fastest** (1, 0, 0, 0), **Greenest** (0.2, 0, 0, 0.8), **Least congestion** (0.3, 0, 0.7, 0).
- Because every term except the fleet penalty is a sum of per-leg costs, Split minimizes it exactly for a given σ. The fleet penalty is applied after Split (P0); a fleet-limited layered Split is P1 (§7.3.4).
- Note for judges: C correlates with T but is not identical — it penalizes using congested roads even when they are still the fastest option, which spreads load.

### 3.5 Constraints and how each is satisfied (REQ-09)
| Constraint | Mechanism | Type |
|---|---|---|
| Each customer served exactly once | Permutation encoding | By construction |
| Routes start and end at depot | Split | By construction |
| Capacity Σd ≤ Q | Split only creates capacity-feasible routes | By construction |
| Single demand > Q | Rejected at scenario creation (HTTP 422) | Validation |
| Fleet size ≤ K | Penalty λ·max(0, m−K) (P0); layered Split (P1) | Penalty → exact |
| Max route duration (optional) | Arc feasibility check in Split | By construction |
| Time windows (P1) | Arc feasibility check in Split (hard) or lateness penalty (soft) | By construction / penalty |
| Unreachable customer | Scenario rejected (all-pairs check) | Validation |

Every saved result passes an **independent feasibility checker** (recomputes coverage, loads, costs from routes). We report "0 infeasible solutions in N runs".

### 3.6 Fleet-aware system-optimal formulation
Let x = fleet flow on road edges implied by R, v⁰ₑ(τ) = background flow. Actual edge time tₑ(x) = t⁰ₑ[1 + a((v⁰ₑ + xₑ)/Cₑ)^b]. The **system optimum** minimizes Σₑ (v⁰ₑ + xₑ)·tₑ(x), i.e., the fleet's own time **plus** the delay it imposes on everyone else. Solved heuristically by a marginal-cost outer loop around QPSO (§6.5).

### 3.7 Shortest-path formulation (REQ-05)
For source s, target t, departure τ: minimize Σ over path edges of the weighted edge cost w_T·tₑ(τₑ)/t_ref + w_C·(tₑ−t⁰ₑ)/c_ref + w_E·Eₑ/E_ref, with τₑ the arrival time at the edge tail. Exact: time-dependent Dijkstra (FIFO network). Metaheuristic: QPSO with priority encoding (§7.11).

### 3.8 QUBO for ordering a route's stops (quantum slot)
For a route with m ≤ 7 customers, depot fixed at both ends. Binary x_{i,p}: customer i at position p. m² variables (≤ 49).
```
H = Σ_i d₀ᵢ x_{i,1} + Σ_i dᵢ₀ x_{i,m} + Σ_{p=1}^{m−1} Σ_{i≠j} dᵢⱼ x_{i,p} x_{j,p+1}
    + A Σ_i (1 − Σ_p x_{i,p})² + A Σ_p (1 − Σ_i x_{i,p})²
```
Penalty A = 3 × (max dᵢⱼ within the route) by default; swept in Phase 6.

---

## 4. Architecture and Stack

### 4.1 Layered architecture
```
 User (planner / analyst / researcher / judge)
        │
 Frontend  React + Vite + TypeScript + react-leaflet + Recharts + TanStack Query + Tailwind
        │  REST /api  +  WebSocket /ws  (fallback: polling; offline: demo mode JSON)
 Backend   FastAPI · pydantic v2 · Job Manager (process pool, progress, cancel, timeout)
        │                    │                        │
 Scenario Service       Engine adapter            Results/Benchmark Service
 (Hyderabad/Synth/      run_job() → qflux         (reads results/, small live runs)
  CVRPLIB, incidents)        │
                    QuantumFlux engine (pure Python package, no web deps)
                    core · algos · traffic · quantum · multiobj · dynamic · sp · bench
        │                                          │
 SQLite (scenarios, jobs, results, convergence)    Files: data/ cache, results/ tables & figures
```
Key design choice: **the engine is a standalone package**. Algorithms are built and tested in parallel with the UI; if the web app fails, every figure can be regenerated from the CLI (`scripts/`).

### 4.2 Technology stack (pinned choices)
| Layer | Choice | Why |
|---|---|---|
| Engine | Python 3.11, NumPy, SciPy, **Numba** | Vectorized swarm + JIT Split/LS |
| Graph | networkx, **osmnx ≥ 2.0** | Real Hyderabad graph (check function names against installed version) |
| Instances | vrplib | CVRPLIB reader |
| Baselines | ortools, pulp (CBC) | Industry + exact references |
| Quantum slot | dimod, **dwave-samplers** (SimulatedAnnealingSampler); qiskit-optimization optional | QUBO today, hardware later |
| Stats | scipy.stats, pandas, matplotlib | Wilcoxon/Friedman, figures |
| Backend | FastAPI, uvicorn, pydantic v2, SQLAlchemy 2 (create_all, no Alembic) | Same language as engine; OpenAPI docs |
| Frontend | React 18, Vite, TypeScript, react-leaflet, Recharts, TanStack Query, Tailwind | Team strength; map + charts |
| Ops | Docker Compose (P1), GitHub Actions pytest (P1) | Reproducible run |
| Testing | pytest, httpx, Vitest (P1), Playwright smoke (P1) | |

### 4.3 Repository layout (frozen)
```
quantumroute/
├── QUANTUMROUTE_MASTER_DOC.md          ← this file
├── README.md
├── docker-compose.yml                  (P1)
├── .env.example
├── configs/
│   ├── default.yaml
│   └── experiments/{bench_core,ablation,alpha_sweep,scaling,hyd_demo}.yaml
├── engine/                             ← pip install -e engine
│   ├── pyproject.toml
│   └── qflux/
│       ├── types.py  rng.py  config.py  api.py        # api.py: run_job() entry point
│       ├── core/{distances,encoding,split,evaluate,localsearch,construct,feasibility}.py
│       ├── algos/{base,qpso,tunneling,pso,ga,sa,aco*,ortools_wrap,milp,heldkarp,cluster}.py
│       ├── quantum/{qubo_route,backends}.py
│       ├── traffic/{hyd_graph,synth_city,profiles,bpr,emissions,td_matrix,fleet_eq,events}.py
│       ├── sp/{td_dijkstra,astar,qpso_path}.py
│       ├── multiobj/pareto.py
│       ├── dynamic/reroute.py
│       ├── explain/templates.py
│       └── bench/{loader,harness,stats,plots}.py
├── backend/
│   └── app/{main.py, settings.py, db.py, models.py, schemas.py,
│            routers/{scenarios,jobs,sp,fleet,benchmarks,quantum,health}.py,
│            services/{job_manager,scenario_service,results_service}.py}
├── frontend/
│   ├── public/demo/*.json             ← demo mode data (exported by scripts/export_demo.py)
│   └── src/{pages,components,api,hooks,types}/
├── scripts/{build_hyd.py, build_synth.py, run_bench.py, run_ablation.py, run_alpha_sweep.py,
│            run_scaling.py, run_fleet_demo.py, run_pareto.py, run_qubo_check.py, export_demo.py}
├── data/{instances/, hyd/, synth/, customers_hyd.csv}
├── results/{runs/, tables/, figures/, demo/, SLIDE_NUMBERS.md}
├── tests/{engine,traffic,api,ui}/
└── docs/{architecture.png, screenshots/}
* = stretch
```

---

## 5. Frozen Contracts (Phase 0 output)

### 5.1 Engine types — `engine/qflux/types.py`
```python
from dataclasses import dataclass, field
import numpy as np

@dataclass
class Instance:
    name: str
    source: str                      # "cvrplib" | "hyderabad" | "synth"
    n: int                           # customers (depot excluded)
    Q: float
    K: int | None                    # fleet limit; None = unlimited
    demand: np.ndarray               # (n+1,), demand[0] = 0
    service: np.ndarray              # (n+1,) minutes, service[0] = 0
    coords: np.ndarray | None        # (n+1, 2): lat/lon (hyd) or x/y
    node_ids: list[int] | None = None          # road-graph node per customer (hyd/synth)
    bks: float | None = None
    distance_convention: str = "exact"         # "nint" | "exact" | "road"
    D: np.ndarray | None = None                # static (n+1, n+1)
    slot_centers: np.ndarray | None = None     # (S,) minutes since midnight
    T_slots: np.ndarray | None = None          # (S, n+1, n+1) minutes, congested
    T0: np.ndarray | None = None               # (n+1, n+1) free-flow time of the same paths
    D_slots: np.ndarray | None = None          # (S, n+1, n+1) km
    E_slots: np.ndarray | None = None          # (S, n+1, n+1) kg CO2
    tau0: float = 480.0

@dataclass
class Weights:
    wT: float = 1.0; wD: float = 0.0; wC: float = 0.0; wE: float = 0.0
    lam: float = 0.5                 # fleet-size penalty

@dataclass
class Refs:
    T: float; D: float; C: float; E: float

@dataclass
class Solution:
    perm: np.ndarray
    routes: list[list[int]]          # customer ids, depot excluded
    F: float
    T: float; D: float; C: float; E: float
    n_vehicles: int
    feasible: bool
    meta: dict = field(default_factory=dict)

@dataclass
class RunRecord:                     # one JSON line in results/runs/*.jsonl
    algo: str; instance: str; seed: int
    budget_type: str; budget: float
    best_F: float; best_T: float; best_D: float; best_C: float; best_E: float
    n_vehicles: int; gap_pct: float | None
    evals_used: int; wall_s: float
    curve: list[tuple[int, float]]   # (evals, best_F) every 100 evals
    config_hash: str
    meta: dict = field(default_factory=dict)   # D28: ls_calls etc.; optional, added in v4.1
```

### 5.2 Engine functions
```python
# core/encoding.py
def spv_decode(keys: np.ndarray) -> np.ndarray                  # argsort(keys) + 1
def encode_perm(perm: np.ndarray, rng, jitter: float = 0.1) -> np.ndarray

# core/split.py   (numba)
def split_static(perm, demand, Q, C) -> tuple[float, np.ndarray]           # cost, pred
def split_td(perm, inst_arrays, w, refs) -> tuple[float, np.ndarray]
def extract_routes(perm, pred) -> list[list[int]]

# core/evaluate.py
class Evaluator:
    def __init__(self, inst: Instance, w: Weights, refs: Refs | None = None): ...
    evals: int                                  # +1 per full evaluation
    def fitness_perm(self, perm) -> float
    def solution(self, perm) -> Solution
    def route_cost(self, route) -> float        # for LS / QUBO; not counted

# core/feasibility.py
def check(inst: Instance, sol: Solution) -> tuple[bool, list[str]]

# core/localsearch.py
def improve_solution(sol, ev, ops=("2opt", "relocate", "swap", "oropt")) -> Solution

# algos/base.py
class Optimizer(Protocol):
    name: str
    def run(self, ev: Evaluator, budget_evals: int | None, budget_s: float | None,
            rng: np.random.Generator, callback=None, should_stop=None,
            init_keys: np.ndarray | None = None) -> tuple[Solution, list[tuple[int, float]]]
# callback(event: dict) every 5 iterations: {"iter", "evals", "best_F", "elapsed_s"}
```

### 5.3 Engine entry point used by the backend — `engine/qflux/api.py`
```python
def build_instance(spec: dict) -> Instance
# spec: {"source": "hyderabad"|"synth"|"cvrplib", "name", "n_customers", "K", "Q", "seed",
#        "tau0", "incidents": [...] }

def run_job(spec: dict, job: dict, progress=None, should_stop=None) -> dict
# job: {"algorithm": "qpso"|"pso"|"ga"|"sa"|"ortools"|"milp", "weights": {...}, "params": {...},
#       "seed": int, "budget": {"evals": int|None, "time_s": float|None},
#       "fleet_mode": "naive"|"user_eq"|"system_opt", "warm_start": {"perm": [...]} | None}
# returns a dict matching §5.5 ResultJSON exactly

def shortest_path(spec: dict, req: dict) -> dict        # §5.4 /shortest-path
def fleet_compare(spec: dict, req: dict) -> dict        # §5.4 /fleet-compare
def solve_route_qubo(req: dict) -> dict                 # §5.4 /quantum/solve-route
```
**Stub rule (Phase 0):** these functions return hard-coded JSON from `frontend/public/demo/` so backend and frontend can start before the engine exists.

### 5.4 REST API (base `/api`, JSON; errors `{"error": {"code", "message"}}`)
| Method | Endpoint | Request | Response | Errors | Priority |
|---|---|---|---|---|---|
| GET | /health | – | `{status, version}` | – | P0 |
| GET | /scenarios | – | `[ScenarioSummary]` | – | P0 |
| POST | /scenarios | `{name, source, n_customers, K, Q, seed, tau0}` | `{scenario}` | 400; 422 INFEASIBLE (demand > K·Q or single demand > Q or unreachable) | P0 |
| GET | /scenarios/{id} | – | `{scenario, customers[{id,lat,lon,demand}], depot}` | 404 | P0 |
| POST | /scenarios/{id}/incidents | `{type: "zone", center:[lat,lon], radius_m, factor, start_min, end_min}` or `{type:"edges", edge_ids, ...}` | `{incident_id, affected_edges}` | 400, 404 | P1 |
| POST | /jobs | `{scenario_id, algorithm, weights, params, seed, budget, fleet_mode, warm_start_job_id?}` | `{job_id, status:"QUEUED"}` | 404; 422 weights ≠ 1; 429 > 2 running | P0 |
| GET | /jobs/{id} | – | `{status, progress, error_message}` | 404 | P0 |
| GET | /jobs/{id}/result | – | ResultJSON | 404; 409 not finished | P0 |
| GET | /jobs/{id}/convergence | – | `[{iter, evals, best_F}]` | 404 | P0 |
| POST | /jobs/{id}/cancel | – | `{status}` | 404; 409 already finished | P1 |
| WS | /ws/jobs/{id} | – | events `{type: progress|completed|failed, iter, evals, best_F}` | close 4404 | P0 |
| POST | /shortest-path | `{scenario_id, source, target, depart_min, algorithm: dijkstra|astar|qpso, weights}` | `{path_geometry, eta_min, cost, runtime_s, gap_pct?}` | 404 no path | P0 (dijkstra), P1 (qpso) |
| POST | /fleet-compare | `{scenario_id, modes:["naive","user_eq","system_opt"], S, weights, seed}` | `{modes:{mode: FleetResult}}` | 404 | P0 |
| POST | /pareto | `{scenario_id, step:0.25, evals_per_point}` | `{points:[{T,D,C,E,job_id}], presets}` | 404 | P1 |
| GET | /benchmarks | – | list of available result tables | – | P0 |
| GET | /benchmarks/{name} | – | `{table:[...], figures:[urls], meta:{runs, budget}}` | 404 | P0 |
| POST | /benchmarks/live | `{instance, algorithms, seeds≤5, budget_evals≤6000}` | `{benchmark_id}` | 422 budget too large | P1 |
| GET | /quantum/validation | – | QUBO validation table (§7.6.4) | – | P0 |
| POST | /quantum/solve-route | `{route_stops, backend: neal|brute|2opt|qiskit}` | `{order, energy, feasible, qubo_matrix, time_s, optimal_cost}` | 422 > 7 stops | P1 |
| GET | /files/{path} | – | figure/CSV from results/ (read-only whitelist) | 404 | P0 |
| POST | /auth/* | – | – | – | P2 |

### 5.5 Result JSON (frontend ↔ backend ↔ engine) — `frontend/src/types/result.ts`
```ts
export interface ResultJSON {
  job_id: string; scenario_id: string; algorithm: string; seed: number;
  status: "COMPLETED" | "COMPLETED_PARTIAL";
  weights: { wT: number; wD: number; wC: number; wE: number; lam: number };
  kpis: { total_time_min: number; total_distance_km: number; congestion_delay_min: number;
          co2_kg: number; vehicles_used: number; fleet_limit: number | null;
          fitness: number; runtime_s: number; evals: number; feasible: boolean };
  routes: Array<{
    vehicle: number; stops: number[]; load: number; capacity: number;
    time_min: number; distance_km: number; congestion_delay_min: number; co2_kg: number;
    depart_min: number; return_min: number;
    geometry: [number, number][];          // lat/lon polyline along roads
    color: string;
  }>;
  edge_flows?: Array<{ geometry: [number, number][]; fleet_flow: number; vc_ratio: number }>;
  explanation: string[];                   // deterministic sentences (§7.14)
  convergence: Array<{ iter: number; evals: number; best_F: number }>;
  refs: { T: number; D: number; C: number; E: number };
  meta: { config_hash: string; instance: string; tau0: number };
}
```
FleetResult = ResultJSON + `{externality_veh_h, max_vc, edges_over_capacity, corridors_used}`.

### 5.6 Database (SQLite, SQLAlchemy 2, `create_all`)
| Table | Fields | Keys |
|---|---|---|
| scenarios | id (uuid), name, source, n_customers, K, Q, seed, tau0, spec_json, created_at | PK id |
| incidents | id, scenario_id, spec_json, created_at | FK scenario_id |
| jobs | id (uuid), scenario_id, algorithm, params_json, weights_json, seed, fleet_mode, status (QUEUED/RUNNING/COMPLETED/COMPLETED_PARTIAL/FAILED/CANCELLED), error_message, started_at, finished_at | FK scenario_id; index status |
| results | job_id (PK/FK), result_json, created_at | unique job_id |
| convergence | job_id, iter, evals, best_F | index (job_id, iter) |
| benchmark_runs | id, spec_json, status, summary_json, created_at | PK id |

Large arrays (matrices, graph) live in `data/` cache files, never in the DB.

### 5.7 Config — `configs/default.yaml`
```yaml
seed_base: 12345
qpso:
  N: 40
  alpha_max: 1.0          # contraction–expansion coefficient (CE)
  alpha_min: 0.5
  alpha_mode: adaptive    # linear | adaptive | fixed
  alpha_fixed: 0.75
  mbest: rank             # uniform | rank
  init: sobol             # uniform | sobol
  ls_every: 10
  ls_top_pbests: 3
  lamarck: true
  diversity_delta: 0.01
  reinit_frac: 0.2
  tunneling: {enabled: true, stagnation: 15, trials: 30, kappa: 8.0}
  qubo_slot: {enabled: true, every: 25, max_stops: 7, backend: neal, num_reads: 200}
pso: {N: 40, w: 0.729, c1: 1.49445, c2: 1.49445, vmax: 0.5}
ga:  {pop: 40, crossover: ox, pc: 0.9, pm: 0.2, tournament: 3, elitism: 2}
sa:  {initial_accept: 0.3, cooling: geometric}
ortools: {first_solution: PATH_CHEAPEST_ARC, metaheuristic: GUIDED_LOCAL_SEARCH, time_limit_s: 30}
milp: {time_limit_s: 600, max_n: 25}
budget: {evals: 12000, time_s: 30}
weights_presets:
  balanced: [0.5, 0.2, 0.2, 0.1]
  fastest:  [1.0, 0.0, 0.0, 0.0]
  greenest: [0.2, 0.0, 0.0, 0.8]
  least_congestion: [0.3, 0.0, 0.7, 0.0]
fleet_penalty_lambda: 0.5
traffic: {bpr_a: 0.15, bpr_b: 4.0, platform_scale_S: 25, fleet_eq_iters: 3}
hyd:
  center: [17.4065, 78.4772]
  radius_m: 12000
  depot_label: "Balanagar logistics hub (illustrative)"
  n_customers: 60
  K: 6
  Q: 200             # D24: was 100, infeasible with 60 x U{5..25} demand
  tau0: 1050            # 17:30
synth: {grid: 20, block_km: 0.5, arterial_every: 5}
limits: {max_customers: 1000, max_iterations: 5000, max_concurrent_jobs: 2, job_timeout_s: 120}
```

---

## 6. Graphs, Traffic, Congestion and Emissions (REQ-01, REQ-06, REQ-12, REQ-18)

### 6.1 Instance sources
| Source | What | Use |
|---|---|---|
| **CVRPLIB** | Standard instances with best-known solutions (BKS) | Credible benchmarks, gaps, ablation, scaling |
| **Hyderabad (OSM)** | Real drive network, 60 illustrative customers | Main demo: time-of-day, fleet impact, incidents, ambulance |
| **SynthCity** | Generated grid city with arterials (seeded) | Unit tests, fast scaling sweeps on road graphs, offline fallback when OSM is unavailable |

### 6.2 Hyderabad graph
```python
G = ox.graph_from_point((17.4065, 78.4772), dist=12000, network_type="drive", simplify=True)
G = ox.add_edge_speeds(G, hwy_speeds=DEFAULT_SPEEDS_KMH)
G = ox.add_edge_travel_times(G)
G = ox.truncate.largest_component(G, strongly=True)       # guarantees reachability
ox.save_graphml(G, "data/hyd/hyd_drive.graphml")            # cache; never download during a demo
```
If the download is slow, reduce to `dist=8000`. Commit the cached graph (or share via drive) so no one downloads twice.
`DEFAULT_SPEEDS_KMH` (free-flow, illustrative): motorway 70, trunk 55, primary 45, secondary 35, tertiary 30, residential/unclassified 20.
**Capacity** Cₑ = lanes × per-lane capacity:
| Class | Default lanes | pcu/h/lane |
|---|---|---|
| motorway / trunk | 3 | 1800 |
| primary | 2 | 1500 |
| secondary | 2 | 1200 |
| tertiary | 1 | 900 |
| residential / other | 1 | 600 |

**Customers** (`data/customers_hyd.csv`): 60 points snapped to graph nodes, sampled (seed 7) around commercial areas: Hitech City, Gachibowli, Madhapur, Kondapur, Kukatpally, Ameerpet, Begumpet, Secunderabad, Banjara Hills, Jubilee Hills, Abids, Dilsukhnagar, LB Nagar, Mehdipatnam, Tolichowki. Demand ~ U{5..25}, service 5 min. Commit the CSV. Variants with 100 and 200 customers for scaling.

### 6.3 SynthCity generator — `traffic/synth_city.py`
- g × g grid (default 20 × 20), block length 0.5 km, coordinates in km; every 5th row/column is an **arterial** (class primary, 2 lanes, 45 km/h), others are local (class residential, 1 lane, 25 km/h); a ring road on the border (class trunk).
- Randomly delete 5% of local edges (seeded) while keeping strong connectivity (re-add if a delete disconnects).
- Customers = random nodes (seeded), depot = centre node.
- Same traffic model as Hyderabad (§6.4) — no second model.

### 6.4 One traffic model (load ratio → BPR)
Background volume v⁰ₑ(τ) = ρ(τ, class(e)) × Cₑ, then BPR:
```
tₑ(τ, x) = t⁰ₑ · [1 + a · ((v⁰ₑ(τ) + xₑ) / Cₑ)^b],   a = 0.15, b = 4
```
Load ratio ρ (illustrative; arterial peak multiplier ≈ 1.8–1.9):
| Slot centre | Arterial (motorway/trunk/primary) | Secondary/tertiary | Residential |
|---|---|---|---|
| 03:00 | 0.30 | 0.20 | 0.10 |
| 07:00 | 1.10 | 0.90 | 0.50 |
| 09:00 | 1.50 | 1.20 | 0.70 |
| 13:00 | 1.10 | 0.90 | 0.50 |
| 17:30 | 1.55 | 1.25 | 0.75 |
| 20:00 | 1.10 | 0.90 | 0.50 |
| 23:00 | 0.50 | 0.40 | 0.20 |

Because arterials saturate more than side roads, the fastest path genuinely changes at peak hours.

### 6.5 Time-dependent matrices with FIFO
For each slot s: set edge weights tₑ(centre_s, x=0); run Dijkstra from the depot and every customer (n+1 runs) to all targets; store T_slots[s], D_slots[s], E_slots[s], the free-flow time T0 of each path, and each path's edge list (needed for fleet flows and map geometry).
Leg query at time t: find centres c_s ≤ t < c_{s+1}, λ = (t − c_s)/(c_{s+1} − c_s), return (1−λ)·M[s] + λ·M[s+1]. Linear interpolation is continuous; FIFO holds when the change in travel time between adjacent centres is smaller than the time between them (assert in test).
Cost: 7 slots × 61 Dijkstras ≈ minutes; cache to `data/hyd/td_<hash>.npz`.

### 6.6 Fleet-aware system-optimal routing (flagship differentiator)

#### 6.6.1 Why marginal cost
If each re-plan uses the *current* congested time, the fleet converges toward **user equilibrium** (each van takes what is fastest for itself). The **system optimum** requires each unit of fleet flow to pay its **marginal** cost, including the delay it inflicts on others:
```
mcₑ(x) = tₑ(x) + (v⁰ₑ + xₑ) · ∂tₑ/∂xₑ = t⁰ₑ[1 + a((v⁰ₑ+xₑ)/Cₑ)^b] + (v⁰ₑ+xₑ) · t⁰ₑ·a·b·(v⁰ₑ+xₑ)^{b−1} / Cₑ^b
```
We **plan** with mcₑ and **evaluate/report** with tₑ.

#### 6.6.2 Loop (Method of Successive Averages)
```
x⁰ = 0
R⁰ = QPSO on matrices from t(v⁰, x⁰)                       # "naive"
for k = 1..3:
    y  = S · flow_of(R^{k−1})                               # pcu/h per road edge, via stored paths
    x^k = x^{k−1} + (1/k)(y − x^{k−1})                      # MSA damping
    rebuild the dispatch-slot matrix with edge weights:
        user_eq    → tₑ(x^k)
        system_opt → mcₑ(x^k)
    R^k = QPSO warm-started from R^{k−1} (50 iterations)
report each R^k with REAL times tₑ(S · flow_of(R^k))
```
Only the dispatch slot is rebuilt (1 slot × (n+1) Dijkstras) to stay fast.

#### 6.6.3 Platform scale factor S — state openly
One plan represents one dispatch wave of a platform; each planned route stands for **S vehicle-equivalents** on the same corridors (default S = 25). Without S, six vans do not measurably change arterial travel times, and claiming otherwise would be wrong. Slide wording: *"We model a platform-scale dispatch wave (S vehicle-equivalents per planned route) so the fleet's own contribution to congestion becomes visible; S is a scenario parameter."*

#### 6.6.4 Metrics
Realized fleet time and CO₂; max V/C; number of edges with V/C > 1; **externality** = Σₑ v⁰ₑ·[tₑ(v⁰+x) − tₑ(v⁰)] in vehicle-hours; distinct corridors used.

### 6.7 CO₂ model (illustrative)
```python
def co2_g_per_km(v_kmh):
    v = max(v_kmh, 5.0)
    return 200 + 3000 / v - 2.5 * v + 0.02 * v ** 2     # ~788 @5, ~477 @10, ~172 @60 km/h
```
Edge CO₂ (kg) = co2_g_per_km(ℓₑ / tₑ) × ℓₑ / 1000. Slide label: "illustrative speed–emission curve (COPERT-shaped); calibration to COPERT light-commercial-vehicle coefficients is finale work."

### 6.8 Incidents — `traffic/events.py`
- `EdgeIncident(edge_ids, start_min, end_min, factor=5.0)`
- `ZoneIncident(center_latlon, radius_m, start_min, end_min, factor=2.5)` — all edges with midpoint inside the circle (UI: user draws a circle on the map).
Both multiply t⁰ₑ inside the window. Only the affected slot matrices are rebuilt. Label incidents as **simulated** on slides; verify any road name used exists in the cached graph.

---

## 7. Algorithms (REQ-03…REQ-08)

### 7.1 Encoding
Particle position X ∈ ℝⁿ (one key per customer). `spv_decode(X) = argsort(X) + 1`. `encode_perm(perm)`: keys[perm[k]−1] = (k + jitter·U(0,1)) / n. **No clipping** — only order matters; ties have probability zero.

### 7.2 Nearest-neighbour construction
Greedy from depot: go to the nearest unserved customer that fits the remaining capacity, else return to depot. Its (T, D, C, E) are the fixed references (§3.4). It also serves as the fallback answer if an optimizer fails. It is **not** injected into the initial swarm (keeps ablations clean; D7).

### 7.3 Prins Split (numba)

#### 7.3.1 Static
```python
@njit(cache=True)
def split_static(perm, demand, Q, C):
    n = perm.shape[0]
    V = np.full(n + 1, np.inf); V[0] = 0.0
    pred = np.full(n + 1, -1, np.int64)
    for i in range(n):
        load = 0.0; cost = 0.0
        for j in range(i, n):
            cj = perm[j]
            load += demand[cj]
            if load > Q:
                break
            if j == i:
                cost = C[0, cj]
            else:
                cost += C[perm[j - 1], cj]
            total = cost + C[cj, 0]
            if V[i] + total < V[j + 1]:
                V[j + 1] = V[i] + total; pred[j + 1] = i
    return V[n], pred
```
Complexity O(n·L), L = max customers per route.

#### 7.3.2 Time-dependent
Same double loop; for each start i reset clock t = τ₀; walking j forward, advance t by service + interpolated leg time, accumulate w_T·T/T_ref + w_D·D/D_ref + w_C·C/C_ref + w_E·E/E_ref; `total` adds the return leg at the current clock. Pass slot arrays as contiguous NumPy arrays.

#### 7.3.3 Lamarckian write-back
After any route-level improvement (LS or QUBO), rebuild the giant tour from the improved routes and set the particle's keys `X = encode_perm(new_perm)`; same for its pbest if improved.

#### 7.3.4 Fleet-limited Split (P1)
Layered DP V[k][j] = min cost to serve the first j customers with k routes, k ≤ K. O(K·n·L). Removes the need for λ.

### 7.4 Local search (numba where easy)
Intra-route 2-opt and or-opt (segments of 1–3); inter-route relocate and swap with capacity checks; first-improvement. LS moves are scored with `route_cost` and are **not** counted as evaluations.
**Schedule (D28):**
1. **gbest:** full LS (2-opt, or-opt, relocate, swap) every `ls_every` = 10 iterations and at final polish.
2. **Memetic rule (D33, replaces D28's trigger):** after each iteration's evaluations, the best ⌈25%⌉ of the **new positions** (by fresh F) get LS (2-opt + relocate + swap, first improvement) with Lamarckian write-back into X; **then** each particle is compared with its pbest. (D28's trigger, "LS on particles whose pbest improved", stopped firing after ≈4 iterations: raw samples never beat LS-polished pbests.)
3. **Fairness:** PSO+LS uses the identical rule. GA+LS applies the same rule to the best ⌈25%⌉ of each generation's offspring (generational GA with elitism: every offspring survives). SA has **no** +LS variant (it is already a local search). **RR+LS** (D34, ablation control) applies the same rule to fresh random keys each iteration.
4. Because LS moves are uncounted, the **time budget is the primary fairness comparison for hybrids**; LS calls per run are recorded in `RunRecord.meta["ls_calls"]`.
5. Every LS call takes the run's deadline and stops when it passes (D31).
6. **Implementation (D41):** on static instances (one traffic slot, e.g. CVRPLIB) every operator uses exact O(1) delta costs from a precomputed leg-cost matrix (2-opt reversal via forward/backward prefix sums, so asymmetric matrices are exact too); loads are maintained incrementally; all inner loops are Numba. Candidate order and the acceptance rule are unchanged, so the local optimum is identical to the generic kernel (equivalence test on 200 seeded tours). Time-dependent instances keep full re-evaluation, only of the 1–2 routes a move touches.

### 7.5 QPSO — `algos/qpso.py`

#### 7.5.1 Update (vectorized)
```python
def qpso_positions(X, P, fP, G, alpha_i, mbest_mode, rng):
    N, D = X.shape
    if mbest_mode == "rank":
        ranks = np.argsort(np.argsort(fP))            # 0 = best
        w = 1.0 / (1.0 + ranks); w /= w.sum()
        mbest = w @ P
    else:
        mbest = P.mean(axis=0)
    phi = rng.random((N, D))
    attractor = phi * P + (1.0 - phi) * G
    u = np.clip(rng.random((N, D)), 1e-12, 1.0)
    sign = np.where(rng.random((N, D)) < 0.5, 1.0, -1.0)
    return attractor + sign * alpha_i[:, None] * np.abs(mbest - X) * np.log(1.0 / u)
```

#### 7.5.2 Contraction–expansion coefficient α
- `linear`: α(t) = α_max − (α_max − α_min)·t/T (default 1.0 → 0.5, from Sun et al. 2012).
- `adaptive` (per particle): αᵢ = α_min + (α_max − α_min)·(fᵢ − f_min)/(f_max − f_min + ε) — better particles exploit, worse explore.
- `fixed`: for the sensitivity sweep. Keep α < 1.78 (convergence bound reported by Sun et al. 2012).
The α sweep (§11.7) includes the prototype's 0.8 → 0.3 schedule.

#### 7.5.3 Main loop
```
init X (scrambled Sobol, or uniform, or warm-start keys), evaluate, P = X, G = best
t = 0, stagnation = 0
while evals < budget and time < limit and not should_stop():
    alpha = strategy(...)
    X = qpso_positions(X, P, fP, G, alpha, mbest_mode, rng)
    X_i <- (rank(X_i) + 0.5) / n for every particle      # D32: order-preserving, tours unchanged, keys bounded
    evaluate all X (1 eval each)
    memetic LS on the best 25% of the new X (by fresh F); Lamarck write-back into X   # D33
    update P, G (elitist)
    if t % ls_every == 0: LS on G; Lamarck write-back
    if qubo_slot.enabled and t % qubo_every == 0 and enough time left: QUBO-reorder G's routes with ≤ 7 stops; accept only if better
    stagnation = 0 if G improved else stagnation + 1
    if tunneling.enabled and stagnation ≥ 15: tunnel (§7.6); stagnation = 0
    if std(f(X)) < δ·mean(f(X)): re-init worst 20% of X (not P)
    every 5 iterations: callback(progress)
    t += 1
final polish: full LS + QUBO slot on G (deadline-aware; skipped if too little time is left, D31)
return G, curve
```
Every step (LS, QUBO slot, tunneling, final polish) receives the run deadline and stops when it passes; the same applies to every algorithm (D31). Rank re-normalisation (D32) is part of the representation, so it is on in QPSO-base, QPSO-full and PSO alike (identical pipeline).
Evaluation counting: each decoded particle = 1 evaluation; LS/QUBO moves use `route_cost` (not counted). That is why we **also** compare on equal wall-clock time (§11.3).

### 7.6 Quantum tunneling escape — `algos/tunneling.py`
```python
def tunnel(best_sol, ev, rng, trials=30, kappa=8.0):
    f0 = best_sol.F
    for _ in range(trials):
        cand_perm, width = random_move(best_sol, rng)   # width = customers moved (1–3)
        f = ev.fitness_perm(cand_perm)                   # counts as an evaluation
        if f < f0:
            return cand_perm, f, "improve"
        h = (f - f0) / f0                                # relative barrier height
        if rng.random() < np.exp(-kappa * width * np.sqrt(h)):
            return cand_perm, f, "tunnel"
    return None, None, "none"
```
- An accepted candidate is encoded and **overwrites the worst particle's X and P**. G is never replaced by a worse solution (elitism preserved).
- Contrast with simulated annealing's exp(−h/T): tunneling probability decays with **width × √height**, favouring structurally small moves even when temporarily costly — the analogy to quantum tunneling through thin barriers. κ = 8 gives ≈ 0.20 acceptance for width 2 and h = 1%. κ ∈ {4, 8, 16} in the ablation.
- Log every tunnel event; the UI can show "tunnel events that later led to a new best".

### 7.7 Quantum-ready sub-route slot — `quantum/`

#### 7.7.1 Where it runs
Only on the **global best**, every 25 iterations and at final polish; only on routes with ≤ 7 customers. Never inside per-particle evaluation (too slow).

#### 7.7.2 Builder
```python
def build_route_qubo(route, dist, A=None):
    m = len(route); nodes = [0] + list(route)
    idx = lambda i, p: i * m + p
    if A is None:
        A = 3.0 * dist[np.ix_(nodes, nodes)].max()
    Q = defaultdict(float)
    for i, ci in enumerate(route):
        Q[(idx(i, 0), idx(i, 0))] += dist[0, ci]
        Q[(idx(i, m - 1), idx(i, m - 1))] += dist[ci, 0]
    for p in range(m - 1):
        for i, ci in enumerate(route):
            for j, cj in enumerate(route):
                if i != j:
                    a, b = sorted((idx(i, p), idx(j, p + 1))); Q[(a, b)] += dist[ci, cj]
    for i in range(m):                                   # each customer exactly one position
        for p in range(m): Q[(idx(i, p), idx(i, p))] -= A
        for p1 in range(m):
            for p2 in range(p1 + 1, m): Q[(idx(i, p1), idx(i, p2))] += 2 * A
    for p in range(m):                                   # each position exactly one customer
        for i in range(m): Q[(idx(i, p), idx(i, p))] -= A
        for i1 in range(m):
            for i2 in range(i1 + 1, m): Q[(idx(i1, p), idx(i2, p))] += 2 * A
    return dict(Q)
```
(The constant 2A from expanding the squares is dropped; it does not change the minimizer.)

#### 7.7.3 Backends — `solve_route_order(route, dist, backend)`
`neal` (dwave-samplers SimulatedAnnealingSampler, num_reads 200) · `brute` (itertools, exact for m ≤ 8) · `heldkarp` (exact, m ≤ 12) · `2opt` · `qiskit` (QAOA via qiskit-optimization, m ≤ 3–4, optional) · `dwave` (Leap stub; needs token). Decode the lowest-energy **feasible** sample; if none is feasible, keep the original route and flag `feasible=False`.
**"One-line swap" claim** = `solve_route_order(..., backend="dwave")`; the pipeline does not change. Keep the stub importable.

#### 7.7.4 Validation experiment (must run — `scripts/run_qubo_check.py`)
On all routes with m = 3..7 from Hyderabad and A-instance solutions: neal vs brute force vs 2-opt. Report feasibility rate, % routes where neal = optimum, mean gap to optimum, time per route; penalty sweep A ∈ {1.5, 3, 6} × max d. This table is the honest evidence for the quantum slot (Quantum Lab screen).

### 7.8 Baselines (REQ-13) — same decoder, same budget, same seeds
| Algorithm | Representation | Operators / parameters | Notes |
|---|---|---|---|
| PSO | keys ∈ ℝⁿ | inertia 0.729, c1 = c2 = 1.49445 (Clerc–Kennedy constriction), vmax 0.5 | Identical pipeline to QPSO except the update rule → isolates the quantum-inspired contribution |
| GA | giant tour | OX crossover, swap + inversion mutation, tournament 3, elitism 2 | Split decode |
| SA | giant tour | 2-opt / relocate / swap moves, geometric cooling tuned to ≈30% initial acceptance | Each move = 1 evaluation |
| ACO* | – | ACS | Stretch only |
| OR-Tools | native | PATH_CHEAPEST_ARC + GUIDED_LOCAL_SEARCH, capacity dimension, integer costs | Time budget only; "industry reference" (we do not claim to beat it) |
| RR+LS (D34) | keys ∈ ℝⁿ | fresh uniform random keys every iteration → Split → the same memetic LS rule and gbest LS as QPSO | **Ablation control, not a headline row**: answers "does the QPSO update add value beyond LS?" Reported whichever way it goes |

Each metaheuristic is reported **plain** and **+LS** (same LS rule as QPSO, D33). Headline rows: QPSO-full, PSO+LS, GA+LS, SA, OR-Tools; plain PSO/GA, QPSO-base and RR+LS appear in the ablation.
Tuning fairness: each algorithm gets the same small tuning budget (≤ 4 configurations on A-n44-k6 only; never on test instances). Log all tuning runs.

### 7.9 Exact methods (REQ-14)
| Method | Scope | Use |
|---|---|---|
| MILP (PuLP/CBC, §3.2) | CVRP n ≤ ~25 (P-n16/19/22), 600 s limit | Optimal value vs QPSO |
| Held-Karp DP O(n²2ⁿ) | Single route, n ≤ 12 | Route-level optimum; QUBO validation |
| Brute force | Route m ≤ 8 | Tests, QUBO validation |
| Dijkstra / A* (time-dependent) | Shortest path | Exact reference for QPSO-SP |

### 7.10 Dynamic re-optimization — `dynamic/reroute.py` (REQ-12)
1. Plan at τ₀; simulate the execution clock.
2. At incident time τₑ, every vehicle is at, or heading to, a known next stop.
3. For each vehicle whose remaining road path crosses an incident edge: (a) recompute road paths between remaining stops with incident weights (road-level detour); (b) re-sequence remaining stops from the current position to the depot (Held-Karp if ≤ 12 stops, else 2-opt); (c) optional relocate moves between affected vehicles (capacity permitting).
4. Unaffected vehicles unchanged.
5. **Next dispatch wave:** warm-started QPSO — 50% of the swarm = previous best keys + Gaussian noise (σ = 0.05), 50% Sobol; one third of the normal iterations.
6. **Accept rule:** keep new routes only if their cost under the new traffic is lower than the old routes re-evaluated under the new traffic; otherwise keep old routes and report it.
Report ETA change per vehicle, delay avoided vs no re-route, re-optimization time, and a warm-vs-cold convergence curve.

### 7.11 Shortest-path suite (REQ-05) — `sp/`
- **TD-Dijkstra** (exact under FIFO):
```python
def td_dijkstra(G, src, dst, t0, edge_time):            # edge_time(u, v, k, t) -> minutes
    best = {src: t0}; pq = [(t0, src)]; prev = {}
    while pq:
        t, u = heapq.heappop(pq)
        if u == dst: break
        if t > best.get(u, inf): continue
        for _, v, k in G.out_edges(u, keys=True):
            ta = t + edge_time(u, v, k, t)
            if ta < best.get(v, inf):
                best[v] = ta; prev[v] = (u, k); heapq.heappush(pq, (ta, v))
    return reconstruct(prev, src, dst), best[dst] - t0
```
- **A\*** with admissible heuristic: straight-line distance / max free-flow speed.
- **QPSO-SP (P1):** priority encoding — a key per node; decode by walking from s to the unvisited out-neighbour with the highest priority until t (dead end → penalty). Search restricted to the subgraph within an ellipse around s–t (keeps n manageable). Report gap to Dijkstra. **Honest note:** for additive costs Dijkstra is exact and faster; QPSO-SP demonstrates the framework covers both problem types and becomes relevant for non-additive objectives (e.g., reliability percentiles — finale).
- **Ambulance demo:** "Station A → Hospital B" at 17:30; a zone incident appears; path + ETA recomputed; both paths shown. Use generic labels unless real locations are verified.

### 7.12 Pareto front — `multiobj/pareto.py` (P1)
Non-dominated archive over (T, D, C, E) (cap 200, crowding-distance pruning). Driver: weight vectors on the simplex (step 0.25), 1,500 evaluations each, warm-started from the previous vector's best. UI presets pick points from the archive. Note: weighted sums only find convex parts of the front; the archive also keeps some non-convex points as a side effect.

### 7.13 Large scale — cluster-first parallel QPSO (REQ-08)
1. Sweep clustering by polar angle around the depot into clusters of ≈ 100–150 customers.
2. One QPSO per cluster, budget proportional to cluster size, run one after another in the same process (D47: one core per run).
3. Concatenate routes; inter-cluster repair via relocate/swap for boundary customers.
4. Report X-n502-k39 and X-n1001-k43: gap to BKS, runtime, runtime vs n. Honest note: state-of-the-art solvers (e.g., HGS) reach very small gaps on X instances; we show **scalability behaviour**, not state-of-the-art quality.

### 7.14 Explainability — `explain/templates.py` (no LLM)
Deterministic sentences from computed numbers, e.g.:
- "Vehicle 2 serves 11 stops (load 92/100) in 63 min, of which 18 min is congestion delay; 21.4 km; 5.1 kg CO₂."
- "Vehicle 4 avoids the simulated incident zone near <area> at +6% distance."
- "System-optimal routing spread the fleet over 9 corridors instead of 5, reducing background delay by X vehicle-hours."
An LLM summary is **not** in scope (it adds hallucination risk without helping the objective).

### 7.15 Complexity summary (REQ-07)
| Component | Cost |
|---|---|
| TD matrices | S slots × (n+1) Dijkstra: O(S·n·(|ℰ| + |𝒩| log|𝒩|)), cached |
| QPSO update | O(N·n) per iteration |
| Decode | sort O(n log n) + Split O(n·L) per particle |
| LS on gbest | O(n²) per pass, every 10 iterations |
| QUBO slot | ≤ 49 variables per route, gbest only |
| Held-Karp | O(n²2ⁿ), n ≤ 12 |
| MILP | exponential worst case; n ≤ 25 |
| Clustered QPSO | ≈ (n/c) × cost(c), parallel |

Objective 3 ("reduce computational complexity") is interpreted as: polynomial-time heuristics vs exponential exact methods, and **fewer evaluations to reach a target quality** — measured, not assumed.

---

## 8. Product: Screens and UX (REQ-15, REQ-17)

### 8.1 Screens (no login in P0)
| # | Screen | Purpose / components | States |
|---|---|---|---|
| S1 | Home | Pitch line, 3 KPI tiles from real results, buttons **Run demo** / Open scenario | Error → static screenshots |
| S2 | Scenario Builder | Source (Hyderabad / SynthCity / CVRPLIB), n, K, Q, seed, departure time; live preview map | 422 infeasible highlighted with fix hint |
| S3 | Run Optimizer | Algorithm, weight sliders + presets, params (N, iterations, α schedule), seed, fleet mode; Start/Cancel; **live convergence chart** | Queued/running %, failed + Retry |
| S4 | Results | Map (routes coloured per vehicle, depot star, congested edges amber), KPI cards (time, distance, congestion delay, CO₂, vehicles, runtime), route table, explanation panel, **Add incident** (draw circle) → Re-optimize, Export | Partial result badge |
| S5 | Fleet Impact | Side-by-side maps naive vs system-optimal (edges coloured by fleet flow), externality, max V/C, CO₂; S slider | – |
| S6 | Shortest Path | Pick source/target on map, departure time, algorithm; path(s) + ETA; incident toggle | 404 no path |
| S7 | Benchmark Studio | Precomputed tables (gap %, mean ± std, p-values, runs, budget), box plots, **live mini-benchmark** (≤ 5 seeds) | Verdict text computed from data |
| S8 | Convergence & Ablation | Overlaid curves vs evaluations (median ± IQR), ablation bars, α sweep | – |
| S9 | Quantum Lab | QUBO validation table, pick a route → QUBO heatmap → backend picker → decoded order vs optimum | 422 > 7 stops |
| S10 | Pareto (P1) | Front scatter (time vs CO₂, colour = congestion), presets update the map | – |

Visual rules: dark navy header, teal primary actions, amber for congestion; one accent colour per algorithm (QPSO teal, PSO amber, GA purple, SA grey, OR-Tools black); 8 px spacing grid; the map is the visual hero.

### 8.2 Key wireframes
```
Results
+--------------------------------------------------------------------------+
| QuantumRoute | Scenario | Run | Results | Fleet | Path | Bench | Quantum |
+--------------------------------------------------------------------------+
| Job #42  QPSO  seed 7  17:30  [Completed]   [+ Incident] [Export]       |
+-----------------------------------------+--------------------------------+
|                                         | Total time        1,234 min    |
|  MAP: routes per vehicle, depot = star, | Congestion delay    254 min    |
|  congested edges = amber, incident =    | Distance            980 km     |
|  red circle                             | CO2                 212 kg     |
|                                         | Vehicles            6 / 6      |
|                                         | Runtime             12.4 s     |
+-----------------------------------------+--------------------------------+
| Route table: Veh | Stops | Load/Q | Time | Delay | Km | CO2             |
| Explanation: "Vehicle 2 avoids the incident zone at +6% distance."       |
+--------------------------------------------------------------------------+
(all numbers above are placeholders)

Fleet Impact
+-----------------------------------+-----------------------------------+
| NAIVE (everyone fastest)          | SYSTEM-OPTIMAL (marginal cost)    |
| map: thick red corridors          | map: flow spread over corridors   |
| externality  X veh-h              | externality  Y veh-h              |
| max V/C      ...                  | max V/C      ...                  |
+-----------------------------------+-----------------------------------+
| S (vehicle-equivalents per route) [==25==]    iterations: 1 2 3        |

Benchmark Studio
| Instances [A-n32][A-n63][A-n80][CMT1] 30 s · [CMT5][X-n101] 60 s   Runs: 30   |
| Algo    | Mean gap % | Std | Best | Wilcoxon p vs QPSO | Evals to 5%            |
| Verdict: computed text from the table, e.g. "On A-n63-k9, QPSO+LS had the lowest mean gap (p=...)." |
```

### 8.3 Demo mode
`VITE_DEMO_MODE=true` makes the frontend read `/demo/*.json` (exported by `scripts/export_demo.py` from real runs) instead of calling the API. Used if the backend, internet or a laptop fails during judging.

---

## 9. Phase-Wise Implementation Plan

Clock: H0 = build start. Team of 6. Critical path: P0 → P1 → P6 → P8 → P9 → P10.

### 9.1 Team roles
| Member | Role | Owns |
|---|---|---|
| M1 | Engine lead | core/, qpso, tunneling, LS, api.py |
| M2 | Benchmark lead | baselines, exact, harness, stats, experiments |
| M3 | Traffic & maps | hyd_graph, synth_city, td_matrix, fleet_eq, events, sp/, reroute |
| M4 | Backend | FastAPI, job manager, WebSocket, DB, results service |
| M5 | Frontend | React screens, map, charts, demo mode |
| M6 | Quantum & pitch lead | QUBO slot, Quantum Lab content, Pareto (P1), PPT, video, Q&A, verification |

With fewer people: merge M2+M6, M4+M5 is not recommended (both are heavy).

### 9.2 Timeline
| Phase | Hours | Owner | Depends on |
|---|---|---|---|
| P0 Setup & contracts | H0–H1 | M1 + all | – |
| P1 Core engine | H1–H6 | M1 | P0 |
| P2 Baselines, exact, harness | H1–H7 | M2 | P0 (uses P1 Split when ready) |
| P3 Graphs & traffic | H1–H7 | M3 | P0 |
| P4 Backend skeleton + mocks | H1–H6 | M4 | P0 |
| P5 Frontend on mocks | H1–H10 | M5 | P0 |
| P6 Quantum-inspired enhancements + QUBO slot | H6–H11 | M1 + M6 | P1 |
| P7 Fleet SO, re-routing, shortest path | H7–H12 | M3 | P1, P3 |
| P8 Integration (milestone at H12) | H10–H14 | M4 + M5 + M1 | P4, P5, P6 |
| P9 Experiments | H11–H17 | M2 (+ M1) | P2, P6 |
| P10 Demo mode, PPT, video, README | H16–H21 | M6 + M5 | P8, P9 |
| P11 Freeze, rehearse, submit | H21–H24 | all | P10 |

**Freeze rule:** no new features after H18 (75%). The last 25% is integration, rehearsal and fixes.

### Phase 0 — Setup & Contracts (H0–H1) [M1, all]
Steps:
1. Create repo per §4.3; `engine/pyproject.toml`; `requirements.txt` (engine) and `backend/requirements.txt`; `frontend` via `npm create vite@latest frontend -- --template react-ts`.
2. Write `qflux/types.py` (§5.1), `qflux/rng.py` (`make_rng(seed) -> np.random.Generator`), `configs/default.yaml` (§5.7), `frontend/src/types/result.ts` (§5.5).
3. Stubs for every engine module with §5.2 signatures raising `NotImplementedError`; `qflux/api.py` stubs returning demo JSON (§5.3).
4. Hand-write `frontend/public/demo/result_demo.json` matching §5.5 (≈ 3 routes, fake numbers clearly marked "MOCK").
5. Start Hyderabad download (M3) and CVRPLIB download (M2).
Acceptance: `pip install -e engine` works; `pytest` runs; `uvicorn backend.app.main:app` serves `/api/health`; `npm run dev` shows a blank page with the header.

### Phase 1 — Core Engine (H1–H6) [M1]
Files: `core/{distances,encoding,split,evaluate,localsearch,construct,feasibility}.py`, `algos/{base,qpso}.py`, `bench/loader.py`.
Steps:
1. Loader: `vrplib.read_instance`; compute D ourselves from coordinates per `distance_convention` (nint for Augerat/Uchoa, exact for CMT); attach BKS from `.sol`.
2. Numba Split (§7.3.1) + TD version (§7.3.2) + `extract_routes`.
3. Evaluator with eval counter and component breakdown (T, D, C, E, m); feasibility checker.
4. NN construction + references.
5. LS operators (§7.4) with capacity checks.
6. Base QPSO: uniform init, uniform mbest, linear α 1.0→0.5, LS every 10, Lamarck. Callback + should_stop.
7. `api.run_job()` for `source=cvrplib`, algorithm `qpso` (real), others stubbed.
Tests: T01–T07 (§10).
Acceptance: all tests pass; QPSO on A-n32-k5 with 12,000 evals finishes < 20 s with a feasible solution; measured gap printed (no target number).

### Phase 2 — Baselines, Exact, Harness (H1–H7) [M2]
Files: `algos/{pso,ga,sa,ortools_wrap,milp,heldkarp}.py`, `bench/{harness,stats,plots}.py`, `scripts/run_bench.py`.
Steps:
1. All metaheuristics implement `Optimizer.run` with the same Evaluator (same Split).
2. Harness: for each (algo, instance, seed) → `RunRecord` appended to `results/runs/<exp>.jsonl`; seed = seed_base + 1000·instance_idx + run_idx; store config hash.
3. Budget modes: evals (12,000) and time (30 s).
4. Stats: mean, std, best, median, worst, gap %; Wilcoxon signed-rank QPSO vs each baseline (paired by run index); Friedman across algorithms.
5. Plots: convergence (median best_F vs evals with IQR band), box plots per instance.
6. OR-Tools sanity check on A-n32-k5 (30 s): gap should be small — if large, the distance convention is wrong.
7. MILP on P-n16-k8, P-n19-k2, P-n22-k8; Held-Karp vs brute force.
Tests: T08–T11.
Acceptance: `python scripts/run_bench.py --exp smoke` (2 instances × 3 algorithms × 3 seeds) produces a CSV table and a convergence PNG.

### Phase 3 — Graphs & Traffic (H1–H7) [M3]
Files: `traffic/{hyd_graph,synth_city,profiles,bpr,emissions,td_matrix,events}.py`, `scripts/{build_hyd,build_synth}.py`, `data/customers_hyd.csv`.
Steps: §6.2–§6.8. Store per-slot path edge lists and free-flow times in the npz; provide `path_geometry(slot, i, j) -> [[lat, lon], ...]` for the map.
Tests: T12–T17.
Acceptance: Hyderabad `Instance` loads from cache in < 5 s; SynthCity builds in < 5 s; QPSO (TD Split) runs on both.

### Phase 4 — Backend Skeleton (H1–H6) [M4]
Files: `backend/app/*` per §4.3.
Steps:
1. FastAPI app, CORS (localhost:5173), error handler producing `{"error": {code, message}}`.
2. SQLAlchemy models §5.6, `create_all` at startup, seed a "Hyderabad-60" and "SynthCity-60" scenario.
3. Routers for every P0 endpoint in §5.4 calling `qflux.api` (stubbed initially).
4. Job manager: `ProcessPoolExecutor(max_workers=2)`; progress events via `multiprocessing.Manager().Queue()` → asyncio task → WebSocket subscribers and DB `convergence` rows; cancel flag via a shared `Event`; timeout → return best-so-far with `COMPLETED_PARTIAL`; exceptions → `FAILED` + message.
5. Validation: pydantic bounds (n ≤ 1000, iterations ≤ 5000, N ≤ 200, weights sum to 1 ± 1e-6), 429 when > 2 running jobs.
6. `/files/{path}` serves only files under `results/` (whitelist, no `..`).
Tests: T18–T27.
Acceptance: OpenAPI at `/docs`; a mock job goes QUEUED → RUNNING → COMPLETED with WebSocket events.

### Phase 5 — Frontend on Mocks (H1–H10) [M5]
Files: `frontend/src/pages/{Home,ScenarioBuilder,RunOptimizer,Results,FleetImpact,ShortestPath,BenchmarkStudio,Convergence,QuantumLab}.tsx`, `components/{RouteMap,KpiCards,RouteTable,ExplanationPanel,ConvergenceChart,StatsTable,BoxPlot,QuboHeatmap,IncidentDrawer}.tsx`, `api/client.ts`, `hooks/useJobProgress.ts`.
Steps:
1. Router + layout + design tokens (§8.1).
2. `api/client.ts`: fetch wrapper mapping `{error:{code,message}}` to toasts; `VITE_DEMO_MODE` switch.
3. `useJobProgress`: WebSocket, falls back to polling `/jobs/{id}` every 2 s.
4. RouteMap: react-leaflet polylines from `routes[].geometry`; OSM tiles; if tiles fail, plain canvas fallback (no basemap).
5. Build S1–S9 against mock JSON. Every screen has empty/loading/error/success states.
Acceptance: all P0 screens clickable on mock data; no console errors.

### Phase 6 — Quantum-Inspired Enhancements + QUBO Slot (H6–H11) [M1, M6]
Files: `algos/qpso.py` (extend), `algos/tunneling.py`, `quantum/{qubo_route,backends}.py`, `scripts/run_qubo_check.py`.
Steps: scrambled Sobol init (`scipy.stats.qmc.Sobol(d=n, scramble=True, seed=...)`), rank mbest, adaptive α, diversity re-init, tunneling (§7.6), QUBO slot (§7.7) — each behind a config flag (needed for ablation).
Tests: T28–T31.
Acceptance: `run_qubo_check.py` writes `results/tables/qubo_validation.csv`; full QPSO runs on A-n63-k9 within budget.

### Phase 7 — Fleet SO, Re-routing, Shortest Path (H7–H12) [M3]
Files: `traffic/fleet_eq.py`, `dynamic/reroute.py`, `sp/{td_dijkstra,astar,qpso_path}.py`, `scripts/run_fleet_demo.py`; `api.fleet_compare`, `api.shortest_path`.
Steps: §6.6, §7.10, §7.11. Save demo artefacts (GeoJSON + metrics JSON) to `results/demo/`.
Tests: T32–T36.
Acceptance: one command regenerates the fleet, incident and ambulance demo artefacts.

### Phase 8 — Integration (H10–H14; milestone at H12) [M4, M5, M1]
Steps: replace stubs with the real engine; end-to-end J1, J2, J4, J5, J6 from the UI; fix contract mismatches (in the doc first).
Acceptance (H12 milestone): judge demo path (§12.1) works **5 times in a row** on the demo laptop.

### Phase 9 — Experiments (H11–H17) [M2, M1 supports]
Run in this order; stop adding when H17 is reached:
1. Core benchmark (`bench_core_v1.yaml`, D29/D39/D40/D43): A-n32-k5, A-n63-k9, A-n80-k10, CMT1 at **30 s**; CMT5, X-n101-k25 at **60 s** (A-n44-k6 and A-n69-k9 are tuning-only, §11.1) × {QPSO-full, PSO+LS, GA+LS, SA, OR-Tools} + RR+LS control, time budget only, **30 runs**. `evals_used` and `ls_calls` are recorded in every RunRecord for transparency. Plain PSO, plain GA and QPSO-base appear in the ablation, not as headline rows. (bench_core v0 was stopped before D41 and is superseded.)
2. Ablation (A-n63-k9, A-n80-k10, 30 s time budget, 10 runs): QPSO-base → +rank mbest → +Sobol → +adaptive α → +memetic LS → +tunneling → +QUBO slot → +diversity (= QPSO-full), with PSO+LS and RR+LS as reference rows; Wilcoxon each row vs the previous. Separately, the only evaluation-budget comparison (D39): plain QPSO-base vs plain PSO (no LS), 12,000 evaluations.
3. α sweep: fixed α ∈ {0.3, 0.5, 0.7, 0.9, 1.0, 1.2}, linear 1.0→0.5, linear 0.8→0.3, adaptive.
4. Scaling (D50: 0.6 s per customer, cap 300 s): X-n101 (60 s, reused from bench_core_v1), X-n200 (120 s) direct; X-n502 (300 s) clustered (D47). X-n1001 and SynthCity scaling are cut (cut list #6).
5. MILP: P-n16/19/22 vs QPSO. The MILP table reports CBC status, best value, bound and gap as measured (e.g. "time limit, gap x%"); it never claims an optimum CBC did not prove. Proven optima for the P instances come from their `.sol` files (T11).
6. Hyderabad: time-of-day comparison (03:00 vs 17:30 plans), fleet demo, incident, ambulance, Pareto (P1).
7. Warm vs cold re-optimization curve.
Every table header states runs, budget type, budget and seeds.
**Gate before starting item 1 (D36):** 0 infeasible solutions, keys bounded, wall time ≤ budget + 2% on every time-budget run, and the gap + evals-to-target (1% and 5% of each run's final value) table reported for both tuning instances (A-n44-k6, A-n69-k9). There is **no** requirement that QPSO wins; the time budget is the primary comparison for hybrids.
Acceptance: `results/tables/*.csv` + `results/figures/*.png` exist for items 1–4 at minimum; `results/SLIDE_NUMBERS.md` started.

### Phase 10 — Demo Mode, PPT, Video, README (H16–H21) [M6, M5]
Steps: `scripts/export_demo.py` → `frontend/public/demo/`; PPT from §13 using only `results/` numbers; 2–3 min screen-recorded video; README (Appendix B).
Acceptance: every slide number traceable in `results/SLIDE_NUMBERS.md`; demo mode works with Wi-Fi off.

### Phase 11 — Freeze, Rehearse, Submit (H21–H24) [all]
Checklist §18. Two full rehearsals under 5 minutes. Tag repo `v-idea-submission`. Export PPT to PDF.

### 9.3 Cut list (cut from the top when behind)
1. ACO baseline
2. Qiskit QAOA backend
3. Pareto screen (keep one "fastest vs greenest" pair)
4. QPSO shortest path (keep Dijkstra/A* ambulance demo)
5. Fleet-limited layered Split (keep λ penalty)
6. X-n1001 (keep X-n502)
7. Live mini-benchmark in the UI (keep precomputed tables)
8. Dynamic re-routing of in-progress vehicles (keep incident before/after plans)
9. Docker Compose
**Never cut:** Split feasibility + checker; QPSO vs PSO vs GA vs OR-Tools on A-instances with convergence plot; ablation on one instance; Hyderabad map; naive vs system-optimal fleet demo; QUBO validation table; honesty statement; demo mode.

### 9.4 Minimum viable evidence (checkpoint at H12)
If the plan is at risk at H12, freeze to: QPSO-full vs PSO+LS vs GA+LS vs SA vs OR-Tools on the 3 core A-instances A-n32-k5, A-n63-k9, A-n80-k10 (30 s time budget, 30 runs; D29, D39, D40) + convergence plot + ablation on A-n63-k9 + Hyderabad Results screen + Fleet Impact screen + Quantum Lab table. That alone is a strong idea-stage submission.

---

## 10. Testing Strategy and Edge Cases

### 10.1 Test table
| ID | Area | Scenario | Expected | Pri |
|---|---|---|---|---|
| T01 | Engine | encode → decode round trip, 1,000 random perms | identical | P0 |
| T02 | Engine | Split output, random keys, n = 50 | every customer once; every load ≤ Q; recomputed cost = returned cost | P0 |
| T03 | Engine | Split on hand-made 5-customer tour | equals brute-force optimal partition | P0 |
| T04 | Engine | LS on random solutions | cost never increases; capacity never violated | P0 |
| T05 | Engine | Same seed twice | identical best cost and routes | P0 |
| T06 | Engine | QPSO 100 iterations | final best ≤ initial best | P0 |
| T07 | Engine | Feasibility checker on corrupted solutions (duplicate, missing, overload) | each detected | P0 |
| T08 | Bench | Harness smoke run | valid JSONL, all fields present | P0 |
| T09 | Bench | Wilcoxon on toy data | matches scipy reference | P0 |
| T10 | Exact | Held-Karp vs brute force, n = 7 | equal cost | P0 |
| T11 | Exact | Heuristic vs proven optimum from the `.sol` file, P-n16/19/22 | heuristic ≥ optimum (within tolerance) | P1 |
| T12 | Traffic | BPR monotonic | time strictly increases with load; equals t⁰ at load 0 | P0 |
| T13 | Traffic | Reachability | every customer ↔ depot reachable in every slot | P0 |
| T14 | Traffic | Peak multiplier | arterial 17:30 multiplier in [1.7, 2.0]; night ≈ 1.0 | P0 |
| T15 | Traffic | FIFO | for 1,000 random (i,j): t + T(t) non-decreasing on a fine time grid | P0 |
| T16 | Traffic | Time dependence matters | ≥ 15% of (i,j) pairs change path between 03:00 and 17:30 (else raise arterial ρ; log decision) | P0 |
| T17 | Traffic | Dijkstra correctness | TD-Dijkstra = networkx shortest_path_length when traffic is static | P0 |
| T18 | API | Create scenario valid | 201 + scenario | P0 |
| T19 | API | Infeasible scenario (demand > K·Q) | 422 INFEASIBLE | P0 |
| T20 | API | Job with weights summing to 0.8 | 422 | P0 |
| T21 | API | Job lifecycle | QUEUED → RUNNING → COMPLETED; result 200 | P0 |
| T22 | API | Result before finish | 409 | P1 |
| T23 | API | Cancel running job | CANCELLED; best-so-far stored | P1 |
| T24 | API | 3 concurrent jobs, limit 2 | 429 | P1 |
| T25 | API | Large instance n = 1000, short timeout | COMPLETED_PARTIAL, feasible | P1 |
| T26 | API | `/files/../secret` | 404 | P0 |
| T27 | API | SQL-injection string as scenario name | stored safely; tables intact | P1 |
| T28 | Quantum | Each QPSO flag toggles behaviour | unit tests with mocks | P0 |
| T29 | Quantum | Tunneling | never worsens G; accepted worse moves land only in the worst particle | P0 |
| T30 | Quantum | QUBO brute backend | equals itertools optimum | P0 |
| T31 | Quantum | QUBO decode | infeasible sample → original route + feasible=False | P0 |
| T32 | Fleet | MSA | ‖xᵏ − xᵏ⁻¹‖ decreasing | P0 |
| T33 | Fleet | Externality system_opt vs naive on demo scenario | ≤ naive; if not, report honestly and investigate S/corridor (log it; do not silently tune) | P0 |
| T34 | Dynamic | Incident zone ×2.5 | delay increases; re-optimized cost ≤ old routes under new traffic | P1 |
| T35 | SP | A* = Dijkstra cost | equal | P0 |
| T36 | SP | QPSO-SP ≥ Dijkstra cost | never better than exact | P1 |
| T37 | UI | Demo path end-to-end | map and charts render; no console errors | P0 |
| T38 | UI | Kill WebSocket mid-job | falls back to polling | P1 |
| T39 | UI | Demo mode with network off | all P0 screens render from JSON | P0 |
| T40 | UI | Tiles unavailable | canvas fallback, banner "offline map" | P1 |

### 10.2 Edge cases
| Case | Handling |
|---|---|
| Empty/invalid input | pydantic 400 with field list; inline form errors |
| Demand > K·Q or single demand > Q | 422 with the offending field highlighted |
| Unreachable customer | scenario rejected at creation |
| Optimizer exception | job FAILED + message; offer NN + 2-opt fallback result |
| Timeout | best-so-far, status COMPLETED_PARTIAL, badge in UI |
| Double-click Start | idempotency key on POST /jobs |
| Tab closed mid-run | job continues; visible in jobs list |
| Very large n | 422 above limit; suggest CLI scaling script |
| No internet | local run; canvas map; demo mode |
| Incident disconnects graph | incident factor is finite (never deletes edges), so graph stays connected |

---

## 11. Experiment Protocol (REQ-10, REQ-11, REQ-13, REQ-14)

### 11.1 Instances
| Set | Instances | n | Use |
|---|---|---|---|
| Augerat P | P-n16-k8, P-n19-k2, P-n22-k8 | 15–21 | MILP exact comparison |
| Augerat A | A-n32-k5, A-n63-k9, A-n80-k10 | 31–79 | Core benchmark, ablation (A-n63, A-n80) |
| Augerat A | A-n44-k6, A-n69-k9 | 43, 68 | **Tuning only**, never in a reported benchmark table (D29, D35) |
| CMT | CMT1, CMT5 | 50, 199 | Core benchmark (classic mid/large) |
| Uchoa X | X-n101-k25 | 100 | Core benchmark + direct large |
| Uchoa X | X-n200-k36 | 199 | Direct large (scaling) |
| Uchoa X | X-n502-k39, X-n1001-k43 | 501, 1000 | Clustered scaling |
| SynthCity | n = 20, 50, 100, 200, 500 | – | Road-graph scaling |
| Hyderabad | 60 (+100, 200) | – | Demos |

### 11.2 Distance conventions
Augerat/Uchoa (EUC_2D): D = nint(Euclidean) — the BKS assume this. CMT: real Euclidean. Gap is computed **only** when our convention matches the BKS convention.

### 11.3 Budgets
**Time budget (primary, and the only budget for LS hybrids; D39):** by instance size class (D43): **30 s for n ≤ 80** (A-n32-k5, A-n63-k9, A-n80-k10, CMT1) and **60 s for n > 80** (CMT5, X-n101-k25); one core per run (D30), deadline-aware (D31). The budget is stated on every table and figure. A time-budget run whose wall time exceeds 1.10× its budget (machine sleep or clock jump) is invalid, kept in `<exp>.invalid.jsonl` and re-run; `run_bench.py` asks the OS not to sleep while it runs. LS moves are not counted as evaluations, so at 12,000 evaluations QPSO-full needed ≈240 s against ≈32 s for GA+LS on A-n44-k6: an evaluation budget is not an equal budget for hybrids. `evals_used` and `ls_calls` are still recorded in every RunRecord.
**Evaluation budget (ablation only):** 12,000 full evaluations, used only to compare the non-LS variants (plain QPSO-base vs plain PSO), where an evaluation really is the unit of work. OR-Tools only on time.
Convergence plots for time-budget runs use wall-clock seconds on the x-axis (`RunRecord.meta["curve_t"]`, D40); evaluation-budget plots use evaluations.

### 11.4 Runs and seeds
**30 runs** per (algorithm, instance) for the core benchmark on the time budget (D40); 10 runs for the ablation, α sweep and scaling; the count is printed in every table and caption. Seeds are deterministic (seed_base + 1000·instance_idx + run_idx, instance_idx from the §11.1 order). Runs execute in up to (physical cores − 1) parallel processes with `NUMBA_NUM_THREADS=1` and `OMP_NUM_THREADS=1`, so each run uses one core and time-budget runs do not compete for CPU.

### 11.5 Metrics
best / mean / std / median / worst of F (and D for CVRPLIB); gap % = (cost − BKS)/BKS × 100; vehicles used; **evaluations to reach within 5% of the final best** (convergence speed); wall time; infeasible count (must be 0).

### 11.6 Statistics
Wilcoxon signed-rank (QPSO-full vs each baseline, α = 0.05; report p and direction). Friedman across instances; Nemenyi critical-difference diagram if time. Ablation: each row vs the previous row.

### 11.7 Required figures
1. Convergence curves (median + IQR vs evaluations) per core instance.
2. Box plots of final gap per instance.
3. Ablation bar chart.
4. α sensitivity (includes 1.0→0.5, 0.8→0.3, adaptive).
5. Runtime and gap vs n (log x).
6. Fleet demo maps + externality bars.
7. Time-of-day: same customers planned at 03:00 vs 17:30.
8. Pareto front (P1).
9. Warm vs cold re-optimization.
10. QUBO validation table.

---

## 12. Demo Strategy

### 12.1 Five-minute live demo (pre-loaded; nothing typed)
| Time | Segment | What we show / say |
|---|---|---|
| 0:00–0:30 | Problem | Tangled-routes map of Hyderabad. "Fleet routing is NP-hard; traffic changes the costs; exact methods stop scaling." |
| 0:30–1:00 | Solution | Pipeline slide. "Quantum-behaved PSO on ordinary CPUs, benchmarked fairly against classical and exact methods." |
| 1:00–1:45 | Live 1 | Hyderabad-60 at 17:30 → Run QPSO → live convergence → Results map + KPIs + explanation |
| 1:45–2:30 | Live 2 | Draw an incident zone → Re-optimize (warm start) → routes shift; before/after delay |
| 2:30–3:15 | Live 3 | Fleet Impact: naive vs system-optimal → externality and V/C drop (real numbers) |
| 3:15–3:50 | Live 4 | Benchmark Studio + convergence overlay → read the verdict honestly |
| 3:50–4:20 | Quantum Lab | QUBO heatmap for one route → neal order vs optimum → "hardware-ready slot" |
| 4:20–5:00 | Impact & next | Who benefits; finale roadmap |

Rule: if QPSO does not win somewhere, say so and show where it helps. Judges reward evidence over hype.

### 12.2 What can go wrong
| Failure | Backup |
|---|---|
| Internet | Local run; canvas map; demo mode; recorded video |
| Backend/API | Demo mode JSON |
| Optimizer too slow | Lower iterations preset; show precomputed result |
| Laptop | Second laptop with the same repo + demo mode; video on phone |
| Map tiles | Canvas fallback |
| Wrong number challenged | `results/SLIDE_NUMBERS.md` open in a tab |

---

## 13. SIH PPT (idea submission, 6 slides)

Fill bracketed values **only** from `results/`.

**Slide 1 — Title:** PS 26137 title, theme, Egreen Quanta, team name, institute. Visual: Hyderabad network with coloured routes.

**Slide 2 — Proposed Solution: QuantumRoute**
- Quantum-behaved PSO for time-dependent fleet routing on Hyderabad's real roads, plus a shortest-path mode.
- **Reduces congestion, not only avoids it:** fleet flow enters the traffic model; routes planned with marginal (system-optimal) cost.
- Minimizes time, distance, congestion delay and CO₂; dispatcher picks Fastest / Greenest / Balanced.
- Quantum-ready slot: route ordering as QUBO, today on a classical sampler, switchable to a quantum annealer.
- Honest positioning line (§1.4).
Visual: naive vs system-optimal maps.

**Slide 3 — Technical Approach**
- Pipeline diagram (§4.1). Equations: QPSO update, fitness (§3.4), BPR + marginal cost.
- Enhancements: rank-weighted mbest, Sobol init, adaptive α, quantum-tunneling escape, optimal Split decoding, Lamarckian local search.
- Stack: Python/NumPy/Numba, OSMnx, OR-Tools, dimod, FastAPI, React + Leaflet.
Visual: flowchart + ablation bars.

**Slide 4 — Feasibility & Viability**
- Working prototype: [N] CVRPLIB instances, [runs] runs, equal budgets, 0 infeasible solutions.
- Snapshot: QPSO-full mean gap [x]% vs PSO [y]% on A-n63-k9 (p = [p]); scaling to n = [1000] in [t] s.
- Risks → mitigations: simulated traffic → live API; hardware access → classical sampler now, Leap later; scale → clustering.
Visual: convergence curves.

**Slide 5 — Impact & Benefits**
- Users: quick-commerce and e-commerce last mile, GHMC services, 108 ambulances, traffic planners.
- Measured in our scenario: externality −[x] vehicle-hours, CO₂ −[y]% (greenest vs fastest), incident delay avoided [z] min.
- Context (cited, dated): logistics cost share of GDP, National Logistics Policy, Smart Cities Mission [VERIFY].
Visual: before/after + CO₂ bars.

**Slide 6 — Research & References:** 8–10 references from §20.

Finale deck flow (10 slides, later): Title · Problem · Why it matters · Solution · How it works · Architecture · Demo · Innovation · Impact · Future scope.

---

## 14. Judge Q&A Preparation
| Question | Defensible answer |
|---|---|
| Is this real quantum computing? | No. QPSO is classical software using quantum-mechanics-derived sampling. Our QUBO slot runs a classical sampler today and can target an annealer without redesign; we show its optimality rate vs brute force. |
| Where exactly is the "quantum"? | (1) QPSO's delta-potential-well sampling, (2) the tunneling escape operator, (3) the QUBO sub-route formulation ready for annealers. |
| Why QPSO over PSO? | One main parameter (α), no velocity, heavy-tailed jumps; our ablation and PSO comparison show measured differences on [instances]. |
| Did QPSO win? | State the actual table. Also: our early untuned prototype had GA ahead; that is why we added optimal Split, local search and equal-budget comparisons. |
| Is the comparison fair? | Same decoder, cost, evaluation budget, time budget, seeds and tuning budget; +LS variants for every baseline; Wilcoxon tests. |
| Are results optimal? | No guarantee. We show gaps to best-known solutions and exact MILP/Held-Karp optima where computable. |
| How do you encode routes? | Random keys → order → optimal Split into capacity-feasible routes. |
| How is congestion modelled? | BPR with class-based time-of-day loads (simulated) + incidents; congestion delay is an explicit objective term. |
| What is "system-optimal"? | Routing that minimizes total delay including what the fleet imposes on others, using marginal cost; with scale factor S stated openly. |
| Why not QAOA / real hardware now? | Current devices handle only tiny instances with noise; we keep the slot and validate on simulators. |
| Is the tunneling operator real tunneling? | It is an analogy: acceptance decays with barrier width × √height, as in tunneling probability; it runs classically. |
| Is traffic real-time? | Simulated; the traffic layer is pluggable for TomTom/HERE/Google feeds at the finale. |
| How large can it go? | Measured: up to n = [1000] with clustering in [t] s; pure-Python limits stated. |
| Compared with OR-Tools? | Included as an industry reference; we do not claim to beat it. |
| Why an ambulance in a VRP project? | The PS asks for shortest path too; time-dependent Dijkstra (exact) plus QPSO-SP for the framework. |
| What data do you store? | Synthetic/illustrative scenarios and results only; no personal location data. |
| Can you finish? | Prototype exists; features beyond the MVP are explicitly listed as finale scope. |

---

## 15. Requirement Traceability (update Status before submission)
| Req | Where | Evidence | Tests | Status |
|---|---|---|---|---|
| REQ-01 Graph model | §6 | Results/Fleet maps | T12–T17 | Planned |
| REQ-02 Formulation | §3 | Slide 3 equations | – | Planned |
| REQ-03 QPSO | §7.5–7.7 | Pseudocode, ablation | T05–T06, T28–T29 | Planned |
| REQ-04 Large-scale VRP | §7.13 | Scaling figure to n = 1000 | T25 | Planned |
| REQ-05 Shortest path | §7.11 | Ambulance demo, QPSO-SP gap | T17, T35–T36 | Planned |
| REQ-06 Time/distance/congestion | §3.4, §6.6, §6.7 | KPIs, fleet demo, Pareto | T33 | Planned |
| REQ-07 Convergence/quality/complexity | §7.15, §11 | Convergence curves, evals-to-5%, p-values | – | Planned |
| REQ-08 Scalability | §7.13, §11.1 | Runtime vs n | T25 | Planned |
| REQ-09 Constraints | §3.5 | "0 infeasible in N runs" | T02, T07, T19 | Planned |
| REQ-10 Convergence analysis | §11.7 | Figures 1, 3, 4, 9 | – | Planned |
| REQ-11 Benchmarking | §11 | Tables with runs/budgets/p | T08–T09 | Planned |
| REQ-12 Dynamic traffic | §6.4, §6.8, §7.10 | Incident demo, warm vs cold | T34 | Planned |
| REQ-13 vs metaheuristics | §7.8 | Benchmark table | – | Planned |
| REQ-14 vs exact | §7.9 | MILP + Held-Karp tables | T10–T11 | Planned |
| REQ-15 Platform | §8 | Live app + demo mode | T37–T40 | Planned |
| REQ-16 Reproducibility | §5.1, §11.4 | Seeds + config hash | T05 | Planned |
| REQ-17 Explainability | §7.14 | Explanation panel | – | Planned |
| REQ-18 Real map | §6.2 | Hyderabad OSM | T13 | Planned |
| REQ-19 Quantum readiness | §7.7 | QUBO validation table | T30–T31 | Planned |
| REQ-20 Auth | – | – | – | P2 / out of scope |

---

## 16. Risk Register
| Risk | Likelihood | Impact | Mitigation | Backup |
|---|---|---|---|---|
| QPSO does not beat baselines | Medium–High (F0) | Medium | Optimal Split, LS, fair tuning, ablation, several instances | Present honest results; show where each method wins |
| OSMnx download slow/fails | Medium | High | Start at H0; 8 km radius; cache and share | SynthCity for all demos |
| Pure Python too slow | Medium | High | Numba from Phase 1; profile on A-n80 early | Smaller n; report measured limits |
| Fleet demo shows no SO benefit | Low–Medium | High | Bottleneck corridor; check S | Present measured result truthfully + theory |
| neal often infeasible | Medium | Low | Penalty sweep | Fallback to 2-opt; report rate |
| Integration delay | Medium | High | Contracts at H1; stubs; H12 milestone | Demo mode + CLI figures |
| Benchmarks exceed time | Medium | Medium | 10 runs; cut list | Fewer instances |
| Unverified citations challenged | Medium | High | §18.2 checklist | Remove anything unverified |
| Live demo failure | Low | High | Rehearse twice; demo mode | Video + static figures |
| Team member unavailable | Low | Medium | Shared repo, this doc | Merge roles per §9.1 |

---

## 17. Decision Log
| ID | Decision | Reason |
|---|---|---|
| D1 | TD-CVRP; time windows P1 | Meets "real-time or simulated traffic" without complicating Split |
| D2 | Random keys + Prins Split | Feasible by construction; standard (Bean 1994; Prins 2004) |
| D3 | Fixed-reference normalization | Population normalization breaks pbest/gbest |
| D4 | Equal evaluations **and** equal time budgets | Fair to hybrids and cheap-step methods |
| D5 | Marginal-cost planning + MSA | Only this targets the system optimum |
| D6 | Scale factor S, disclosed | Small fleets do not move BPR; honesty |
| D7 | No NN seed in initial swarm | Clean ablations |
| D8 | QUBO only on gbest, validated vs brute force | Runtime + honest claim |
| D9 | One traffic model for Hyderabad and SynthCity | No double counting |
| D10 | Linear interpolation of slot matrices | FIFO |
| D11 | Hyderabad | Local knowledge; verifiable demo |
| D12 | React + FastAPI; Streamlit dropped | Team strength; better judge UX; demo mode covers offline |
| D13 | CVRPLIB (no Solomon) in prototype | Variant match |
| D14 | α for QPSO; (a, b) for BPR | Removes symbol clash |
| D15 | Default α 1.0→0.5; 0.8→0.3 only in sweep | Literature default; prototype tuned on one instance |
| D16 | No key clipping | Clipping creates ties |
| D17 | Congestion delay term C with floor on C_ref | PS names congestion explicitly |
| D18 | Fleet limit via λ penalty (P0), layered Split (P1) | Time |
| D19 | No login in P0 | Judge value vs hours |
| D20 | Names: QuantumRoute (platform), QuantumFlux (engine) | Keeps both teams' work recognisable |
| D21 | Tuning budget ≤ 4 configs per algorithm on A-n44-k6 only | Avoids tuning on test instances |
| D22 | System optimum counts delay to **all** traffic: mc = t + (v⁰+x)·∂t/∂x (v3 used x·∂t/∂x, which only counts the fleet's own delay) | Matches the externality metric and the "reduce congestion for everyone" claim |
| D23 | Dispatch wave treated as a 1-hour flow: each route traversal = S vehicles/h on its edges | Makes flow units consistent with BPR capacity (pcu/h) |
| D24 | (2026-09-30, Person B) Hyderabad default Q = 200 (was 100) | 60 customers × U{5..25} demand ≈ 1,005 units > K·Q = 600, so the default demo was infeasible; Q = 200 keeps 6 vans at ≈ 84% utilisation |
| D25 | (2026-09-30, Person B) `Instance.T0[i,j]` = free-flow time of the **free-flow-fastest** path; C = max(T(t) − T0, 0) | Paths differ per slot, so "free-flow time of the same path" is not one 2-D matrix; this keeps C ≥ 0. Per-slot own-path free-flow times are kept in the TD cache (`T0_path`) |
| D26 | (2026-09-30, Person B) An incident is applied to every slot whose centre lies in its window; if none does, to the slot nearest the window midpoint | Short incidents between slot centres would otherwise have no effect on slot matrices. Shortest path (TD-Dijkstra/A*) applies incidents exactly by time |
| D27 | (2026-09-30, Person B) Python 3.11+ (3.13 tested) | Laptop has 3.13; all pinned deps support it |
| D28 | (2026-10-04, Person A) Memetic LS rule: LS (2-opt + relocate + swap, Lamarckian) on every particle that improved its pbest, capped at the best 25% of the swarm per iteration; gbest LS every 10 iterations kept. Same rule for PSO+LS; GA+LS applies LS to surviving offspring with the same cap; no SA+LS. LS calls recorded in the new optional `RunRecord.meta` field (§5.1) | Smoke run: with LS only on gbest + top-3 pbests, raw particles never beat the polished gbest, so QPSO's best was fixed after ≈100 evaluations (flat convergence curve). LS moves are uncounted, so the time budget is primary for hybrids |
| D29 | (2026-10-04, Person A) Core benchmark set: A-n32-k5, A-n63-k9, A-n80-k10, CMT1, CMT5, X-n101-k25; A-n44-k6 is tuning-only (§11.1 wins over the old §9 Phase 9 list) | Never tune on test instances (D21) |
| D30 | (2026-10-04, Person A) 10 runs per (algorithm, instance); up to (physical cores − 1) parallel processes, each with NUMBA_NUM_THREADS=1, OMP_NUM_THREADS=1 | 30 runs of the time budget alone ≈ 12 h on one core; one core per run keeps time budgets fair |
| D31 | (2026-10-04, Person A) Deadline-aware LS, QUBO slot, tunneling and final polish for every algorithm; QUBO slot and final polish skipped when too little time is left; OR-Tools gets the remaining time | Smoke run: QPSO overran a 5 s budget by up to 30%. Acceptance: wall ≤ budget + 2% |
| D32 | (2026-10-04, Person A) Order-preserving rank re-normalisation each iteration in the key swarm (QPSO and PSO): X_i ← (rank(X_i) + 0.5)/n | Diagnosed on A-n44-k6: keys diverged to max\|X\| ≈ 10⁴–10⁵ even with fixed α = 0.75 and α inside [α_min, α_max]. Not a code bug: random-key decoding is invariant to order-preserving rescaling, so a pbest is accepted at any scale; one far coordinate in P drags mbest and the attractor, producing larger heavy-tailed (ln 1/u) jumps in that coordinate. Re-normalising leaves every decoded tour unchanged and bounds the keys in (0, 1) |
| D33 | (2026-10-04, Person A) Memetic trigger: LS on the best ⌈25%⌉ of the new positions (by fresh F), Lamarckian write-back, then the pbest comparison; same rule for PSO+LS and GA+LS. 4th and final tuning configuration | With D28's trigger the memetic step stopped after ≈4 iterations (median fX/fP ≈ 1.96 on A-n44-k6: raw samples never beat polished pbests) |
| D34 | (2026-10-04, Person A) Control algorithm RR+LS: fresh random keys each iteration → Split → the same LS and memetic rule, same budget. Ablation row only | Answers "does the QPSO update add value beyond LS?"; reported whichever way it goes |
| D35 | (2026-10-04, Person A) A-n69-k9 (BKS 1159, proven optimal) added as a second tuning-only instance; in no test set | Behaviour at larger n without looking at test instances. No configuration changes after the A-n69-k9 runs |
| D36 | (2026-10-04, Person A) Gate for starting bench_core: 0 infeasible, keys bounded, wall ≤ budget + 2%, gap + evals-to-1%/5% table reported for both tuning instances. Replaces "the convergence curve keeps improving" | A converged hybrid is flat by design; flat at ≈1% gap = converged, flat at 5–10% = premature convergence, which the table shows. No requirement that QPSO wins |
| D37 | (2026-10-04, Person A) `RunRecord.meta: dict` added to the frozen `types.py` (+ contract test). Additive and backward compatible (default empty dict). Noted in MERGE_NOTES.md for Person B | Per-run diagnostics (LS calls, QUBO calls, max\|key\|) without a second results file |
| D38 | (2026-10-04, Person A) Fleet limit for CVRPLIB: K = k from the name for Augerat A/P, K = ∞ for CMT and Uchoa X (was K = ∞ for all). Gap tables report `fleet_violations` (runs with more than K vehicles) | P-n22-k8: SA found 590 with 9 vehicles, below the proven optimum 603, which assumes 8 vehicles. A gap against an optimum for a different fleet rule is not a fair comparison. Not a tuning change |
| D38+ | (2026-10-04, Person A) Under K = k a final solution with m > k counts as infeasible for gap purposes: no gap is computed for it, it is excluded from distance/gap statistics and tests, and tables report the number of such runs per algorithm (`fleet_violations`) | Decided with D38 |
| D39 | (2026-10-04, Person A) bench_core uses the **30 s time budget only**, for all algorithms. The 12,000-evaluation budget is kept only in the ablation for the non-LS variants (plain QPSO-base vs plain PSO). evals_used and ls_calls are recorded in every RunRecord | LS moves are uncounted: at 12,000 evals QPSO-full used ≈240 s vs GA+LS ≈32 s on A-n44-k6 (≈8 h per run estimated on CMT5), so equal evaluations are not equal work |
| D40 | (2026-10-04, Person A) 30 runs per (algorithm, instance) for bench_core (replaces D30's 10; D30's parallel rule stays). Time-budget convergence plots use wall time: `RunRecord.meta["curve_t"]` = (elapsed_s, best_F) at each improvement (additive, see MERGE_NOTES.md) | The time-only benchmark fits in ≈1 h on 11 workers |
| D41 | (2026-10-04, Person A) Exact O(1)-delta LS kernels for static instances (`core/ls_static.py`); same move order and acceptance, so the same local optimum; time-dependent instances unchanged (full re-evaluation of the touched routes) | Profiling: ≈90% of LS time was full route re-evaluation (A-n69-k9 random tour: 233 ms median per memetic LS call, ≈57k route-cost calls). After D41: 1.8 ms (≈130×). A performance fix applied to all hybrids equally, not tuning. bench_core_v0 (stopped, partial) is superseded |
| D42 | (2026-10-04, Person A) Granular neighbourhoods **not adopted** | Only required if the median LS call stayed > 20 ms on A-n69-k9 random tours after D41; it is 1.8 ms |
| D43 | (2026-10-04, Person A) Time budget by size class: 30 s for n ≤ 80 (A-n32, A-n63, A-n80, CMT1), 60 s for n > 80 (CMT5, X-n101); stated on every table and figure. Time-budget runs longer than 1.10× budget are invalid and re-run | Equal time per size class; at n = 199, 30 s gives too few iterations for any swarm (QPSO-full: 44–55 iterations in 60 s on CMT5). Guard added after the laptop entered Modern Standby for ≈28 min during a smoke run (every run then reported ≈1,607 s) |
| D44 | (2026-10-04, Person A) Timing-fairness check of bench_core_v1: 11 workers = physical cores (12) − 1, so not oversubscribed; runs are interleaved per (instance, seed) in a fixed algorithm order, not in algorithm blocks. Restart with a shuffled order was therefore **not triggered**; v1 continues. Recorded: CPU i7-1360P is hybrid (4 performance + 8 efficiency cores, 16 threads), power plan Balanced; per-run speed spread on the same instance up to ≈1.26–1.29× (SA moves per 30 s). From now on every RunRecord stores start/end timestamps and each launch writes `<exp>.run_info.json` (CPU, cores, power plan, workers, commit) | Needed to check throttling drift (gap vs start time) and to state the hardware with every table |
| D45 | (2026-10-04, Person A) **Pre-registered before any bench_core_v1 result was seen:** supplementary row QPSO-noQUBO (QPSO-full with the QUBO slot disabled) on the bench_core instances, same seeds and budgets, run right after bench_core_v1 (`bench_core_v1_noqubo.yaml`) | Measures what the QUBO slot costs or adds inside the time budget |
| D47 | (2026-10-04, Person A) Cluster-first QPSO (`algos/cluster.py`): sweep clusters of ≈125 customers, one QPSO-full per cluster with a time share ∝ cluster size (90% of the budget), then relocate/swap/2-opt repair over all routes in the remaining time. Clusters run **sequentially** in one process, not in parallel as §7.13 said | Keeps one core per run (D30), so the clustered X-n502 run gets the same CPU as every other run |
| D48 | (2026-10-04, Person A) Backend (P4) contract details: `jobs` table gains `progress` (for GET /jobs/{id}) and `idempotency_key` (double-click Start, §10.2), both additive. Shape errors → 400 INVALID_INPUT with the field list; semantic errors → 422. Frontend job params map to engine names (N; alpha_start/alpha_end → linear α schedule; iterations → N×iterations evaluations when no budget; default 10 s); a time budget is capped at the job timeout. `/quantum/solve-route` takes customer ids of the seeded Hyderabad-60 scenario and uses its dispatch-slot travel times. MILP is not a platform job (422). `/benchmarks` lists every summary table with its kind (benchmark / tuning / smoke) | §5.4 does not say how the frontend params or the solve-route distances are defined; these choices keep the UI working without changing result.ts |
| D49 | (2026-10-04, Person A) **Pre-registered before any bench_core_v1 quality number was seen:** P/E-core robustness check after the queue, on an idle machine: 4 workers each pinned to one logical CPU of its own P-core (logical 0, 2, 4, 6 on the i7-1360P), QPSO-full, QPSO-noQUBO, PSO+LS, GA+LS, RR+LS on A-n63-k9 and A-n80-k10, 30 s, 10 runs, bench_core_v1 seeds (`pcore_check.yaml`). Verdict = whether the mean-gap ranking and the Wilcoxon conclusions (QPSO-full vs each, α = 0.05) match bench_core_v1 on the same instances and seeds; if not, both results are reported and flagged, neither dropped. From now on every experiment shuffles the algorithm order within each (budget, instance, seed) group with a fixed seed and stores a 0.2 s CPU-speed calibration per run (`meta.cpu_calib_ops_s`) | bench_core_v1 used a fixed in-group order on a hybrid CPU; per-run speed varied up to ≈1.26–1.29× |
| D50 | (2026-10-04, Person A) Scaling budget rule: 0.6 s per customer, capped at 300 s, stated on the figure. X-n101-k25 = 60 s (its bench_core_v1 runs are reused, not re-run), X-n200-k36 = 120 s, X-n502-k39 = 300 s | Removes the 30 s vs 60 s mismatch for X-n101 between scaling and bench_core_v1 |
| D46 | (2026-10-04, Person A) Time-dependent instances (Hyderabad, SynthCity): local search scores candidate moves with O(1) deltas on the dispatch-slot static proxy matrix and keeps a move only if the full time-dependent cost of the touched routes improves (`core/ls_td_proxy.py`; `improve_routes(td_proxy=True)` default, `td_proxy=False` = generic kernel). Never worse than its input, 0 infeasible (tested); not move-for-move identical to the generic kernel | Hyderabad-60, 100 random tours, memetic operators: median LS call 128 ms → 3.0 ms (≈42×); final TD cost proxy/generic 1.0022 on average per tour (better on 55, worse on 45) |
| D51 | (2026-10-04, Person A) Memory-pressure audit of every timed run (throughput vs the median of the same experiment, budget, instance, algorithm; CPU calibration; wall/budget): runs below 0.75× or above 1.02× budget are re-run with the same seeds and the old record is kept in `<exp>.d51_replaced.jsonl`. Experiments run from a standalone runner (`scripts/runner.py`, PID lock, ≥ 4 GB free to start, memory log every minute, new runs pause below 2 GB) | Claude Code's memory guard stopped the queue at ≈15:5x with 0.9 GB free; 25 runs were flagged, clustered at 14:52, 15:37–15:39 and 15:46; after two re-run passes 0 are flagged |
| D52 | (2026-10-04, Person A) Backend: the job timeout is passed to the optimizer as its time budget (cap), so LS/QUBO/polish stop at it (D31); COMPLETED_PARTIAL when the cap was binding. T25 uses SynthCity n = 399 instead of n = 1000 (the default 20×20 grid has 399 customer nodes; a 1000-customer road scenario needs ≈1–1.5 GB for its per-slot path store). MILP: no `-threads` option (`-threads 1` hangs the bundled CBC build). QPSO imports the neal sampler at construction (the first call in a process otherwise paid the import inside the time budget) | Found by the API job tests, the MILP run and the D31 deadline test |
| D53 | (2026-10-04, decided by the team after the bench_core_v1 report) Default "QuantumRoute engine" for the app and the demos = **QPSO-noQUBO** (QPSO-full with the QUBO slot off; registry name `qpso_noqubo`; backend `algorithm: "qpso"` runs it unless `params.qubo_slot = true`, and results are labelled `qpso_noqubo` / `qpso_full`). The QUBO slot stays available (Quantum Lab, backend toggle). QPSO-full is reported next to it everywhere | Pre-registered D45 row; best Friedman average rank at 30 s (1.88 vs 2.88 for QPSO-full) |
| D55 | (2026-10-04, Person A) OR-Tools wrapper: arc costs and demands registered as C++-side matrix/vector (`RegisterTransitMatrix`, `RegisterUnaryTransitVector`) instead of Python callbacks. Same model, same search parameters. Only the OR-Tools rows of bench_core_v1 and scaling were re-run (same seeds and budgets); old rows kept in `<exp>.d55_replaced.jsonl` | Diagnostic (CMT1, 30 s): Python callback 598 solutions, 5.91% gap; matrix 1,580 solutions, 0.58% gap; vehicles, scaling (×1000 for exact distances), capacity, time limit and first-solution strategy checked and correct |
| D56 | (2026-10-04, Person A) Reporting: Wilcoxon p-values Holm–Bonferroni-corrected per table (`p_holm`; family = all comparisons in that table); effect size = paired difference in gap points (median and mean); a second headline comparison set with QPSO-noQUBO as the reference; heuristic-vs-exact table for the P instances (`p_small`: QPSO-noQUBO, PSO+LS, OR-Tools, 10 s, 10 runs, K = k) next to the MILP table | Multiple comparisons per table; magnitude next to significance |
| … | Add new decisions with date/time | |

---

## 18. Pre-Submission Checklists

### 18.1 Product & demo
- [ ] Every P0 test green; feasibility checker passes on every stored result
- [ ] Judge demo path works 5 times in a row; demo mode works offline
- [ ] Two rehearsals under 5 minutes; video recorded and on two devices
- [ ] README complete; no secrets committed; `.env.example` present
- [ ] Traceability Status column updated with real evidence

### 18.2 Evidence & citations [VERIFY]
- [ ] Every slide number listed in `results/SLIDE_NUMBERS.md` with its source file
- [ ] BKS values taken from `.sol` files, not memory
- [ ] 2026 arXiv items from the research reports (§20.2): open each, confirm authors/title/year and that it says what we cite it for; drop any that fail
- [ ] India statistics (logistics cost % of GDP, congestion cost, transport CO₂): primary source (Economic Survey / NITI Aayog / DPIIT LEADS / IEA) with year, or remove
- [ ] Every road/place name in demos exists in the cached graph
- [ ] Honesty statement on slide 2 and in README

---

## 19. Finale Roadmap
1. Time windows in Split; Solomon benchmarks. 2. Layered fleet-limited Split; multi-depot. 3. Live traffic feed (TomTom/HERE/Google) replacing load-ratio profiles; calibrate BPR a, b for Hyderabad corridors. 4. COPERT-calibrated emissions; EV energy variant. 5. Full dynamic VRP with rolling horizon. 6. QUBO scaling via decomposition; QAOA comparison; D-Wave Leap run if access is available. 7. GPU/Numba-parallel swarm; worker queue (RQ/Celery); Docker deploy with HTTPS. 8. Reliability-aware routing (90th-percentile arrival) and QPSO-SP for non-additive objectives. 9. Login/roles, audit log, multi-tenant.

---

## 20. References

### 20.1 Core (well established)
1. Sun, J., Feng, B., Xu, W. (2004). Particle Swarm Optimization with Particles Having Quantum Behavior. IEEE CEC 2004, 325–331.
2. Sun, J., Fang, W., Wu, X., Palade, V., Xu, W. (2012). Quantum-Behaved Particle Swarm Optimization: Analysis of Individual Particle Behavior and Parameter Selection. Evolutionary Computation 20(3), 349–393.
3. Bean, J.C. (1994). Genetic Algorithms and Random Keys for Sequencing and Optimization. ORSA Journal on Computing 6(2), 154–160.
4. Prins, C. (2004). A Simple and Effective Evolutionary Algorithm for the Vehicle Routing Problem. Computers & OR 31(12), 1985–2002.
5. Dantzig, G.B., Ramser, J.H. (1959). The Truck Dispatching Problem. Management Science 6(1), 80–91.
6. Toth, P., Vigo, D. (2014). Vehicle Routing: Problems, Methods, and Applications (2nd ed.). SIAM.
7. Miller, C.E., Tucker, A.W., Zemlin, R.A. (1960). Integer Programming Formulation of Traveling Salesman Problems. JACM 7(4), 326–329.
8. Held, M., Karp, R.M. (1962). A Dynamic Programming Approach to Sequencing Problems. J. SIAM 10(1), 196–210.
9. Malandraki, C., Daskin, M.S. (1992). Time Dependent Vehicle Routing Problems. Transportation Science 26(3), 185–200.
10. Ichoua, S., Gendreau, M., Laporte, G. (2003). Vehicle Dispatching with Time-Dependent Travel Times. EJOR 144(2), 379–396.
11. Wardrop, J.G. (1952). Some Theoretical Aspects of Road Traffic Research. Proc. ICE 1(3), 325–362.
12. Sheffi, Y. (1985). Urban Transportation Networks. Prentice-Hall.
13. Bureau of Public Roads (1964). Traffic Assignment Manual.
14. Uchoa, E. et al. (2017). New Benchmark Instances for the Capacitated Vehicle Routing Problem. EJOR 257(3), 845–858.
15. Augerat, P. et al. (1995). Computational Results with a Branch and Cut Code for the CVRP. Research report.
16. Christofides, N., Mingozzi, A., Toth, P. (1979). The Vehicle Routing Problem. In Combinatorial Optimization, Wiley.
17. Derrac, J. et al. (2011). A Practical Tutorial on the Use of Nonparametric Statistical Tests. Swarm and Evolutionary Computation 1(1), 3–18.
18. Boeing, G. (2017). OSMnx. Computers, Environment and Urban Systems 65, 126–139.
19. Han, K.-H., Kim, J.-H. (2002). Quantum-Inspired Evolutionary Algorithm. IEEE TEVC 6(6), 580–593.
20. Kadowaki, T., Nishimori, H. (1998). Quantum Annealing in the Transverse Ising Model. Physical Review E 58(5), 5355.
21. Lucas, A. (2014). Ising Formulations of Many NP Problems. Frontiers in Physics 2:5.
22. Clerc, M., Kennedy, J. (2002). The Particle Swarm — Explosion, Stability, and Convergence. IEEE TEVC 6(1), 58–73.
23. Pillac, V. et al. (2013). A Review of Dynamic Vehicle Routing Problems. EJOR 225(1), 1–11.
24. Vidal, T. (2022). Hybrid Genetic Search for the CVRP: Open-Source Implementation and SWAP* Neighborhood. Computers & OR 140.
25. Gen, M., Cheng, R., Wang, D. (1997). Genetic Algorithms for Solving Shortest Path Problems. IEEE ICEC 1997. (priority-based encoding) [VERIFY exact title/venue]

### 20.2 Recent / frontier (from the research reports — all [VERIFY] before citing)
- Wu et al. (2026). Rank-Refined QPSO. arXiv:2607.10284
- Rezk & Gora (2026). GNN-Guided Graph Coarsening and Adaptive QUBO Penalties for CVRPTW. arXiv:2609.04593
- Sharma & Lau (2026). Qubit-Scalable CVRP via Lagrangian Knapsack Decomposition. arXiv:2604.22194
- Giang et al. (2025). Quantum Graph Attention Network for VRP. arXiv:2511.15175
- Li et al. (2024). Halfway Escape Optimization. arXiv:2405.02850
- Kumar et al. (2024). GPU-Parallelized QIEO. arXiv:2412.08992
- Abdellaoui et al. (2026). RL-Assisted Reoptimization Under Disruptions. arXiv:2607.20901

---

## 21. Glossary
- **VRP / CVRP / TD-CVRP:** vehicle routing; capacitated; time-dependent capacitated.
- **Giant tour:** all customers in one sequence, later split into routes.
- **Split (Prins):** shortest-path DP that optimally cuts a giant tour into feasible routes.
- **Random keys / SPV:** real vector whose sorted order gives a permutation.
- **QPSO:** PSO without velocity; positions sampled from a Laplace-like distribution around an attractor.
- **mbest:** (weighted) mean of personal bests.
- **α (contraction–expansion coefficient):** controls the spread of QPSO sampling.
- **Lamarckian write-back:** copy local-search improvements back into the particle's keys.
- **Tunneling operator:** stagnation escape; accepts worse moves with probability exp(−κ·width·√height).
- **BPR:** link travel time vs volume/capacity function, t = t⁰(1 + a(v/c)^b).
- **Congestion delay:** travel time above free-flow time.
- **User equilibrium vs system optimum:** everyone minimizing their own time vs minimizing total time.
- **Marginal cost:** the extra total delay caused by one more vehicle on an edge.
- **MSA:** Method of Successive Averages (damped flow update).
- **FIFO:** leaving later never means arriving earlier.
- **QUBO:** quadratic unconstrained binary optimization — input format of quantum annealers.
- **Held-Karp:** exact DP for a single tour, O(n²2ⁿ).
- **BKS / gap:** best-known solution; % above it.
- **Pareto front:** solutions where no objective improves without another worsening.

---

## Appendix A — Agent Prompts per Phase (paste into Antigravity)

**Common header (prepend to every prompt):**
```
You are implementing part of QuantumRoute. The single source of truth is
QUANTUMROUTE_MASTER_DOC.md in the repo root. Read §0, §1.4, §3, §4.3 and §5 fully before coding.
Use the exact module paths, dataclasses, function signatures, API shapes and JSON schema from §5.
Implement ONLY the phase below. Do not edit files owned by other phases.
Write the listed tests, run them, and stop when every acceptance criterion passes.
If the doc is ambiguous or wrong, stop and report the exact section instead of improvising.
Python 3.11; seeded numpy.random.Generator only; no global random state; no invented numbers in UI or docs.
```

**P0 — Setup & Contracts**
```
Phase 0 (§9 Phase 0). Create the repository layout of §4.3 exactly. Write engine/qflux/types.py (§5.1),
qflux/rng.py, configs/default.yaml (§5.7), frontend/src/types/result.ts (§5.5). Create stubs with §5.2/§5.3
signatures. qflux/api.py stubs must return frontend/public/demo/result_demo.json (write it by hand to match
§5.5, values marked "MOCK"). Scaffold FastAPI with /api/health and a Vite React-TS app with the header.
Acceptance: pip install -e engine works; pytest runs; /api/health returns 200; npm run dev renders.
```

**P1 — Core Engine**
```
Phase 1 (§9 Phase 1; algorithms §7.1–§7.5.3 without tunneling/QUBO/Sobol/rank/adaptive).
Implement bench/loader.py (CVRPLIB via vrplib, compute distances per §11.2), core/encoding.py,
core/split.py (numba, static + time-dependent, §7.3.1–7.3.3), core/evaluate.py (components T,D,C,E,m,
fixed references §3.4), core/construct.py (nearest neighbour), core/feasibility.py, core/localsearch.py
(§7.4), algos/base.py, algos/qpso.py (base: uniform init, uniform mbest, linear alpha 1.0→0.5,
LS every 10, Lamarck, callback every 5 iterations, should_stop), and qflux/api.run_job for
source=cvrplib, algorithm=qpso. Tests T01–T07. Acceptance: A-n32-k5, 12,000 evals, < 20 s, feasible.
```

**P2 — Baselines, Exact, Harness**
```
Phase 2 (§9 Phase 2; §7.8, §7.9, §11). Implement algos/pso.py, ga.py, sa.py, ortools_wrap.py, milp.py,
heldkarp.py using the shared Evaluator; bench/harness.py (RunRecord JSONL, deterministic seeds, evals and
time budgets, config hash), bench/stats.py (summary, gap %, Wilcoxon, Friedman), bench/plots.py
(median+IQR convergence vs evals, box plots), scripts/run_bench.py with --exp from configs/experiments.
Tests T08–T11. Acceptance: --exp smoke produces a CSV table and a convergence PNG in results/.
```

**P3 — Graphs & Traffic**
```
Phase 3 (§9 Phase 3; §6.1–§6.8). Implement traffic/hyd_graph.py (download+cache, speeds, capacities by
class), traffic/synth_city.py (§6.3), profiles.py (load-ratio table §6.4), bpr.py, emissions.py (§6.7),
td_matrix.py (slot matrices T,D,E, free-flow T0, stored path edge lists, linear interpolation,
path_geometry), events.py (EdgeIncident, ZoneIncident), scripts/build_hyd.py, build_synth.py,
data/customers_hyd.csv (60 customers, seed 7, areas listed in §6.2). Extend qflux/api.build_instance for
hyderabad and synth. Tests T12–T17. Acceptance: Hyderabad instance loads from cache < 5 s.
```

**P4 — Backend**
```
Phase 4 (§9 Phase 4; §5.4, §5.6). FastAPI app with CORS, error envelope, SQLAlchemy models and
create_all, seeded scenarios, all P0 endpoints of §5.4 calling qflux.api, job manager with
ProcessPoolExecutor(2), progress via Manager().Queue to WebSocket + convergence table, cancel, timeout
→ COMPLETED_PARTIAL, failures → FAILED, pydantic limits from §5.7, 429 for >2 running jobs,
/files whitelist under results/. Tests T18–T27 with pytest + httpx.
Acceptance: /docs lists endpoints; a job streams WebSocket events and ends COMPLETED.
```

**P5 — Frontend**
```
Phase 5 (§9 Phase 5; §8). React + Vite + TS + react-leaflet + Recharts + TanStack Query + Tailwind.
Build screens S1–S9 of §8.1 with the components listed in §9 Phase 5, api/client.ts with error-envelope
toasts and VITE_DEMO_MODE, hooks/useJobProgress.ts (WebSocket, polling fallback every 2 s), RouteMap with
canvas fallback when tiles fail. Every screen has empty/loading/error/success states. Colours per §8.1.
Work against /demo/*.json until the backend is ready. Acceptance: all P0 screens clickable, no console errors.
```

**P6 — Quantum-Inspired Enhancements + QUBO**
```
Phase 6 (§9 Phase 6; §7.5–§7.7). Extend algos/qpso.py with scrambled Sobol init, rank-weighted mbest,
adaptive alpha, diversity re-init, all behind config flags of §5.7. Implement algos/tunneling.py (§7.6)
with elitism rules. Implement quantum/qubo_route.py (§7.7.2) and quantum/backends.py (neal via
dwave-samplers, brute, heldkarp, 2opt, optional qiskit, dwave stub). Wire the QUBO slot on gbest every
25 iterations for routes ≤ 7 stops. scripts/run_qubo_check.py writes results/tables/qubo_validation.csv
(§7.7.4 incl. penalty sweep). Tests T28–T31.
```

**P7 — Fleet SO, Re-routing, Shortest Path**
```
Phase 7 (§9 Phase 7; §6.6, §7.10, §7.11). Implement traffic/fleet_eq.py (naive / user_eq / system_opt,
marginal cost, MSA, scale factor S, realized metrics incl. externality), dynamic/reroute.py (incident
handling + warm start + accept rule), sp/td_dijkstra.py, sp/astar.py, sp/qpso_path.py (priority encoding,
ellipse subgraph), qflux/api.fleet_compare and shortest_path returning §5.4 shapes with geometries,
scripts/run_fleet_demo.py saving GeoJSON + metrics to results/demo/. Tests T32–T36.
```

**P8 — Integration**
```
Phase 8 (§9 Phase 8). Replace stubs with the real engine. Verify journeys J1, J2, J4, J5, J6 (§2.4)
end-to-end from the UI. Any contract mismatch: fix §5 in the doc first, then both sides.
Acceptance: demo path §12.1 runs 5 times in a row on the demo laptop.
```

**P9 — Experiments**
```
Phase 9 (§9 Phase 9; §11). Create configs/experiments/*.yaml and run items 1–7 in order within the time
box. Every table and figure states runs, budget type, budget, seeds. Produce figures §11.7.
Start results/SLIDE_NUMBERS.md mapping each headline number to its file. Never edit numbers by hand.
```

**P10 — Demo Mode, PPT, README**
```
Phase 10 (§9 Phase 10; §8.3, §12, §13, Appendix B). scripts/export_demo.py exports real results to
frontend/public/demo/. Draft the 6 SIH slides from §13 using only results/ numbers. Write README from
Appendix B. Check demo mode with the network off (T39).
```

---

## Appendix B — README template
```
# QuantumRoute
Quantum-inspired (QPSO) fleet routing on congestion-aware road graphs, with a fair benchmark studio.
SIH 2026 · PS 26137 · Egreen Quanta

## Honesty statement
QPSO is a classical algorithm inspired by quantum mechanics; it runs on ordinary CPUs. The QUBO slot
uses a classical sampler today. Traffic is simulated. No quantum speedup is claimed.

## What it does
Hyderabad road graph + BPR traffic · QPSO (Split decoding, local search, tunneling) · PSO/GA/SA/OR-Tools/
MILP/Held-Karp baselines · system-optimal fleet routing · incident re-routing · shortest path ·
QUBO sub-route slot · benchmark studio with seeds and statistics.

## Quick start
pip install -e engine && pip install -r backend/requirements.txt
python scripts/build_hyd.py            # uses cached graph if present
uvicorn backend.app.main:app --port 8000
cd frontend && npm install && npm run dev      # http://localhost:5173
# Offline: VITE_DEMO_MODE=true npm run dev

## Reproduce figures
python scripts/run_bench.py --exp bench_core
python scripts/run_ablation.py
python scripts/run_alpha_sweep.py
python scripts/run_scaling.py
python scripts/run_fleet_demo.py
python scripts/run_qubo_check.py

## Architecture
React → FastAPI (REST + WebSocket) → QuantumFlux engine (qflux) → SQLite + results/

## Team
[Member 1] … [Member 6]

## Limitations and future scope
Simulated traffic; heuristic (no optimality guarantee); illustrative CO₂ curve; see §19 of the master doc.
```
