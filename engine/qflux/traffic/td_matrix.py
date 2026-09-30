"""Time-dependent customer matrices with stored road paths (§6.5).

For each slot s: edge weights t_e(centre_s, x) -> Dijkstra from the depot and every customer ->
T_slots[s], D_slots[s], E_slots[s] plus the edge list of every (i, j) path (for fleet flows and map
geometry). Leg values at an arbitrary time are linearly interpolated between slot centres.

Congestion delay reference: `T0[i, j]` is the free-flow travel time of the free-flow-fastest path, so
C = T(t) - T0 >= 0 always ("time above free flow"). The free-flow time of each slot's own path is kept
in `T0_path` for reference.
"""
import hashlib
import json
from dataclasses import dataclass

import numpy as np

from qflux.config import load_config

from . import events
from .bpr import bpr_time, marginal_cost
from .emissions import edge_co2_kg
from .profiles import SLOT_CENTERS, load_ratio, slot_weights
from .roadnet import RoadNet, path_nodes

CACHE_VERSION = 1


def edge_times(net: RoadNet, t: float, x: np.ndarray | None = None, incidents=None,
               mode: str = "time", inc_factor: np.ndarray | None = None) -> np.ndarray:
    """Per-edge minutes at time t with extra fleet flow x (pcu/h).

    mode="time" -> BPR travel time t_e; mode="mc" -> marginal cost mc_e (system-optimal planning).
    """
    tr = load_config()["traffic"]
    v = load_ratio(t, net.group) * net.capacity
    if x is not None:
        v = v + x
    t0 = net.t0_min
    if inc_factor is not None:
        t0 = t0 * inc_factor
    elif incidents:
        t0 = t0 * events.factor_at(net, incidents, t)
    f = marginal_cost if mode == "mc" else bpr_time
    return f(t0, v, net.capacity, tr["bpr_a"], tr["bpr_b"])


@dataclass
class SlotPaths:
    ptr: np.ndarray            # ((n+1)*(n+1)+1,) offsets into edges
    edges: np.ndarray          # concatenated edge indices

    def get(self, i: int, j: int, m: int) -> np.ndarray:
        k = i * m + j
        return self.edges[self.ptr[k]:self.ptr[k + 1]]


def all_pairs(net: RoadNet, terminals: np.ndarray, w: np.ndarray, t_real: np.ndarray | None = None):
    """Paths between all terminal pairs minimising w; sums of real time, length, CO2, t0 along them.

    Returns (W, T, D, E, T0path, SlotPaths). `t_real` defaults to w.
    """
    t_real = w if t_real is None else t_real
    m = len(terminals)
    dist, pred, lookup = net.shortest_paths(terminals, w)
    co2 = edge_co2_kg(net.length_km, t_real)
    W = dist[:, terminals]
    T = np.zeros((m, m)); D = np.zeros((m, m)); E = np.zeros((m, m)); T0 = np.zeros((m, m))
    ptr = np.zeros(m * m + 1, np.int64)
    chunks = []
    for i in range(m):
        for j in range(m):
            if i != j:
                nodes = path_nodes(pred[i], int(terminals[i]), int(terminals[j]))
                if not nodes:
                    raise ValueError(f"terminal {j} unreachable from {i}")
                e = lookup(nodes[:-1], nodes[1:]) if len(nodes) > 1 else np.zeros(0, np.int64)
                T[i, j] = t_real[e].sum(); D[i, j] = net.length_km[e].sum()
                E[i, j] = co2[e].sum(); T0[i, j] = net.t0_min[e].sum()
                chunks.append(e)
                ptr[i * m + j + 1] = len(e)
    ptr = np.cumsum(ptr)
    edges = np.concatenate(chunks) if chunks else np.zeros(0, np.int64)
    return W, T, D, E, T0, SlotPaths(ptr, edges.astype(np.int64))


@dataclass
class TDBundle:
    net: RoadNet
    terminals: np.ndarray       # (n+1,) node index per customer, 0 = depot
    slot_centers: np.ndarray
    T_slots: np.ndarray
    D_slots: np.ndarray
    E_slots: np.ndarray
    T0: np.ndarray              # free-flow time of the free-flow-fastest path
    T0_path: np.ndarray         # (S, n+1, n+1) free-flow time of each slot's own path
    paths: list[SlotPaths]
    incidents: list

    @property
    def m(self) -> int:
        return len(self.terminals)

    def path(self, s: int, i: int, j: int) -> np.ndarray:
        return self.paths[s].get(i, j, self.m)

    def path_geometry(self, s: int, i: int, j: int) -> list[list[float]]:
        """[[lat, lon], ...] along the road path used from customer i to j in slot s."""
        e = self.path(s, i, j)
        if len(e) == 0:
            p = self.net.node_xy[self.terminals[i]]
            return [[float(p[0]), float(p[1])]]
        nodes = np.concatenate([self.net.eu[e[:1]], self.net.ev[e]])
        return self.net.node_xy[nodes].round(6).tolist()

    def leg(self, i: int, j: int, t: float) -> tuple[float, float, float, float]:
        """(T, D, C, E) of leg i->j departing at time t (linear interpolation between slots)."""
        s, s1, lam = slot_weights(t, self.slot_centers)
        T = (1 - lam) * self.T_slots[s, i, j] + lam * self.T_slots[s1, i, j]
        D = (1 - lam) * self.D_slots[s, i, j] + lam * self.D_slots[s1, i, j]
        E = (1 - lam) * self.E_slots[s, i, j] + lam * self.E_slots[s1, i, j]
        return T, D, max(T - self.T0[i, j], 0.0), E

    # ---- persistence ----
    def save(self, path) -> None:
        arrs = dict(terminals=self.terminals, slot_centers=self.slot_centers, T_slots=self.T_slots,
                    D_slots=self.D_slots, E_slots=self.E_slots, T0=self.T0, T0_path=self.T0_path)
        for s, p in enumerate(self.paths):
            arrs[f"ptr{s}"] = p.ptr
            arrs[f"edges{s}"] = p.edges.astype(np.int32)
        np.savez_compressed(path, **arrs)

    @classmethod
    def load(cls, path, net: RoadNet, incidents) -> "TDBundle":
        z = np.load(path)
        S = len(z["slot_centers"])
        paths = [SlotPaths(z[f"ptr{s}"], z[f"edges{s}"].astype(np.int64)) for s in range(S)]
        return cls(net, z["terminals"], z["slot_centers"], z["T_slots"], z["D_slots"], z["E_slots"],
                   z["T0"], z["T0_path"], paths, incidents)


def build_bundle(net: RoadNet, terminals: np.ndarray, incidents=None,
                 centers: np.ndarray = SLOT_CENTERS) -> TDBundle:
    incidents = list(incidents or [])
    per_slot = events.slot_incidents(incidents, centers)
    S, m = len(centers), len(terminals)
    Ts, Ds, Es, T0p = (np.zeros((S, m, m)) for _ in range(4))
    paths = []
    for s, c in enumerate(centers):
        f = events.factor_for(net, per_slot[s])
        w = edge_times(net, c, inc_factor=f)
        _, Ts[s], Ds[s], Es[s], T0p[s], sp = all_pairs(net, terminals, w)
        paths.append(sp)
    # free-flow fastest time between terminals (reference for congestion delay)
    dist0, _, _ = net.shortest_paths(terminals, net.t0_min)
    T0 = dist0[:, terminals]
    return TDBundle(net, np.asarray(terminals), np.asarray(centers, float), Ts, Ds, Es, T0, T0p, paths, incidents)


def cache_key(parts: dict) -> str:
    parts = dict(parts, v=CACHE_VERSION)
    return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:12]


def get_bundle(net: RoadNet, terminals, incidents, cache_dir, key_parts: dict) -> TDBundle:
    """Load from `cache_dir/td_<hash>.npz` or build and cache."""
    from pathlib import Path
    key = cache_key(dict(key_parts, terminals=list(map(int, terminals)),
                         incidents=[events.to_spec(i) for i in incidents or []]))
    path = Path(cache_dir) / f"td_{key}.npz"
    if path.exists():
        return TDBundle.load(path, net, list(incidents or []))
    b = build_bundle(net, np.asarray(terminals), incidents)
    path.parent.mkdir(parents=True, exist_ok=True)
    b.save(path)
    return b


# Registry so api-level helpers can find the bundle behind an Instance (Instance is a frozen contract).
_REGISTRY: dict[str, TDBundle] = {}


def register(name: str, bundle: TDBundle) -> None:
    _REGISTRY[name] = bundle


def bundle_for(inst) -> TDBundle:
    try:
        return _REGISTRY[inst.name]
    except KeyError:
        raise KeyError(f"no TD bundle for instance {inst.name!r}; build it with qflux.api.build_instance")
