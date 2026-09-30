"""Simulated incidents (§6.8). Both kinds multiply free-flow time t0 inside their time window.

Factors are finite (edges are never deleted), so the graph stays connected (§10.2).
"""
from dataclasses import dataclass, field

import numpy as np

from .roadnet import RoadNet


@dataclass
class EdgeIncident:
    edge_ids: list[int]
    start_min: float
    end_min: float
    factor: float = 5.0
    kind: str = field(default="edges", init=False)


@dataclass
class ZoneIncident:
    center_latlon: tuple[float, float]
    radius_m: float
    start_min: float
    end_min: float
    factor: float = 2.5
    kind: str = field(default="zone", init=False)


Incident = EdgeIncident | ZoneIncident


def from_spec(d: dict) -> Incident:
    """Parse the §5.4 incident request body."""
    if d.get("type", "zone") == "zone":
        return ZoneIncident(tuple(d["center"]), float(d["radius_m"]), float(d["start_min"]), float(d["end_min"]),
                            float(d.get("factor", 2.5)))
    return EdgeIncident([int(e) for e in d["edge_ids"]], float(d["start_min"]), float(d["end_min"]),
                        float(d.get("factor", 5.0)))


def to_spec(inc: Incident) -> dict:
    if isinstance(inc, ZoneIncident):
        return {"type": "zone", "center": list(inc.center_latlon), "radius_m": inc.radius_m,
                "start_min": inc.start_min, "end_min": inc.end_min, "factor": inc.factor}
    return {"type": "edges", "edge_ids": list(inc.edge_ids), "start_min": inc.start_min,
            "end_min": inc.end_min, "factor": inc.factor}


def affected_edges(net: RoadNet, inc: Incident) -> np.ndarray:
    if isinstance(inc, EdgeIncident):
        return np.asarray(inc.edge_ids, dtype=np.int64)
    radius_km = inc.radius_m / 1000.0
    d = net.dist_km(net.edge_midpoints(), np.asarray(inc.center_latlon, float))
    return np.flatnonzero(d <= radius_km)


def is_active(inc: Incident, t: float) -> bool:
    return inc.start_min <= t < inc.end_min


def factor_at(net: RoadNet, incidents: list[Incident], t: float) -> np.ndarray:
    """Per-edge multiplier on t0 at time t (product over active incidents)."""
    f = np.ones(net.E)
    for inc in incidents:
        if is_active(inc, t):
            f[affected_edges(net, inc)] *= inc.factor
    return f


def slot_incidents(incidents: list[Incident], centers: np.ndarray) -> list[list[Incident]]:
    """Incidents applied to each slot matrix: active at the slot centre, or — if the window contains no
    centre — assigned to the slot nearest the window midpoint, so short incidents are never dropped."""
    out: list[list[Incident]] = [[] for _ in centers]
    for inc in incidents:
        hit = [s for s, c in enumerate(centers) if is_active(inc, c)]
        if not hit:
            mid = (inc.start_min + inc.end_min) / 2.0
            hit = [int(np.argmin(np.abs(centers - mid)))]
        for s in hit:
            out[s].append(inc)
    return out


def factor_for(net: RoadNet, incidents: list[Incident]) -> np.ndarray:
    """Per-edge multiplier applying all given incidents unconditionally."""
    f = np.ones(net.E)
    for inc in incidents:
        f[affected_edges(net, inc)] *= inc.factor
    return f
