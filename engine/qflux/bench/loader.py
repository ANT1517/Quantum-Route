"""CVRPLIB loader (§9 Phase 1): distances computed by us per §11.2, BKS attached from the .sol file."""
from pathlib import Path

import numpy as np
import vrplib

from qflux.config import REPO_ROOT
from qflux.core.distances import euclidean
from qflux.types import Instance

INSTANCE_DIR = REPO_ROOT / "data" / "instances"


def convention_for(name: str) -> str:
    return "exact" if name.upper().startswith("CMT") else "nint"


def read_bks(path: Path) -> float | None:
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        if line.strip().lower().startswith("cost"):
            return float(line.split()[1])
    return None


def load_instance(name: str, directory: Path | None = None) -> Instance:
    d = Path(directory or INSTANCE_DIR)
    raw = vrplib.read_instance(str(d / f"{name}.vrp"), compute_edge_weights=False)
    coords = np.asarray(raw["node_coord"], dtype=float)
    depot = int(np.asarray(raw.get("depot", [0])).ravel()[0])
    if depot != 0:                                   # put the depot first
        order = [depot] + [i for i in range(len(coords)) if i != depot]
        coords = coords[order]
        demand = np.asarray(raw["demand"], float)[order]
    else:
        demand = np.asarray(raw["demand"], float)
    n = len(coords) - 1
    conv = convention_for(name)
    service = np.zeros(n + 1)
    if "service_time" in raw:
        st = np.asarray(raw["service_time"], float).ravel()
        service = np.full(n + 1, float(st[0])) if st.size == 1 else st
        service[0] = 0.0
    return Instance(name=name, source="cvrplib", n=n, Q=float(raw["capacity"]), K=None, demand=demand,
                    service=service, coords=coords, bks=read_bks(d / f"{name}.sol"),
                    distance_convention=conv, D=euclidean(coords, conv), tau0=0.0)


def read_solution_routes(name: str, directory: Path | None = None) -> list[list[int]]:
    sol = vrplib.read_solution(str(Path(directory or INSTANCE_DIR) / f"{name}.sol"))
    return [list(map(int, r)) for r in sol["routes"]]
