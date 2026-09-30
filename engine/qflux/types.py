"""Frozen engine types (master doc §5.1). Do not change without updating §5 + Decision Log."""
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
