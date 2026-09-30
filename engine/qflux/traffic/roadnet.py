"""Compact array form of a road graph, shared by Hyderabad (OSM) and SynthCity.

Loading a large GraphML takes tens of seconds, so everything downstream (TD matrices, fleet flows,
shortest paths, map geometry) works on these arrays, which load from .npz in well under a second.
"""
from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from .profiles import ARTERIAL, RESIDENTIAL, SECONDARY

# Free-flow speeds (km/h, illustrative) and capacity per class (§6.2)
CLASS_TABLE = {
    #  highway       speed lanes pcu/h/lane group
    "motorway":      (70, 3, 1800, ARTERIAL),
    "trunk":         (55, 3, 1800, ARTERIAL),
    "primary":       (45, 2, 1500, ARTERIAL),
    "secondary":     (35, 2, 1200, SECONDARY),
    "tertiary":      (30, 1, 900, SECONDARY),
    "residential":   (20, 1, 600, RESIDENTIAL),
}
MAX_SPEED_KMH = 70.0


def class_params(highway) -> tuple[float, float, int]:
    """(speed_kmh, capacity_pcu_h, group) for an OSM highway tag (str or list; *_link maps to its base)."""
    if isinstance(highway, (list, tuple)):
        highway = highway[0] if highway else "residential"
    base = str(highway).replace("_link", "")
    speed, lanes, pcu, group = CLASS_TABLE.get(base, CLASS_TABLE["residential"])
    return float(speed), float(lanes * pcu), group


@dataclass
class RoadNet:
    node_id: np.ndarray        # (N,) original graph node ids (OSM ids or synth ids)
    node_xy: np.ndarray        # (N, 2) [lat, lon] (hyderabad) or [y, x] in km (synth)
    eu: np.ndarray             # (E,) tail node index
    ev: np.ndarray             # (E,) head node index
    length_km: np.ndarray      # (E,)
    t0_min: np.ndarray         # (E,) free-flow time
    capacity: np.ndarray       # (E,) pcu/h
    group: np.ndarray          # (E,) ARTERIAL / SECONDARY / RESIDENTIAL
    latlon: bool = True

    @property
    def N(self) -> int:
        return len(self.node_id)

    @property
    def E(self) -> int:
        return len(self.eu)

    def save(self, path) -> None:
        np.savez_compressed(path, node_id=self.node_id, node_xy=self.node_xy, eu=self.eu, ev=self.ev,
                            length_km=self.length_km, t0_min=self.t0_min, capacity=self.capacity,
                            group=self.group, latlon=np.array(self.latlon))

    @classmethod
    def load(cls, path) -> "RoadNet":
        z = np.load(path)
        return cls(node_id=z["node_id"], node_xy=z["node_xy"], eu=z["eu"], ev=z["ev"],
                   length_km=z["length_km"], t0_min=z["t0_min"], capacity=z["capacity"],
                   group=z["group"], latlon=bool(z["latlon"]))

    # ---- geometry helpers -------------------------------------------------------------------
    def dist_km(self, a, b) -> np.ndarray:
        """Straight-line distance (km) between coordinate arrays of shape (..., 2)."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        if not self.latlon:
            return np.linalg.norm(a - b, axis=-1)
        a, b = np.radians(a), np.radians(b)
        dlat, dlon = b[..., 0] - a[..., 0], b[..., 1] - a[..., 1]
        h = np.sin(dlat / 2) ** 2 + np.cos(a[..., 0]) * np.cos(b[..., 0]) * np.sin(dlon / 2) ** 2
        return 2 * 6371.0 * np.arcsin(np.sqrt(h))

    def nearest_node(self, point) -> int:
        return int(np.argmin(self.dist_km(self.node_xy, np.asarray(point, dtype=float))))

    def edge_midpoints(self) -> np.ndarray:
        return (self.node_xy[self.eu] + self.node_xy[self.ev]) / 2.0

    # ---- shortest paths ---------------------------------------------------------------------
    def best_parallel(self, w: np.ndarray) -> np.ndarray:
        """Indices of the cheapest edge for each distinct (u, v) pair under weights w."""
        key = self.eu.astype(np.int64) * self.N + self.ev
        order = np.lexsort((w, key))
        k = key[order]
        first = np.ones(len(k), bool)
        first[1:] = k[1:] != k[:-1]
        return order[first]

    def shortest_paths(self, sources, w: np.ndarray):
        """Dijkstra from each source under edge weights w (> 0).

        Returns (dist (k, N), pred (k, N), edge_lookup) where edge_lookup(u, v) gives the edge index used.
        """
        sel = self.best_parallel(w)
        mat = csr_matrix((w[sel], (self.eu[sel], self.ev[sel])), shape=(self.N, self.N))
        dist, pred = dijkstra(mat, directed=True, indices=np.asarray(sources), return_predecessors=True)
        keys = self.eu[sel].astype(np.int64) * self.N + self.ev[sel]
        kord = np.argsort(keys)
        skeys, sedges = keys[kord], sel[kord]

        def edge_lookup(u, v) -> np.ndarray:
            q = np.asarray(u, np.int64) * self.N + np.asarray(v, np.int64)
            return sedges[np.searchsorted(skeys, q)]

        return dist, pred, edge_lookup

    def adjacency(self):
        """Out-edge CSR: edges of node u are out_edges[out_ptr[u]:out_ptr[u+1]]."""
        order = np.argsort(self.eu, kind="stable")
        ptr = np.zeros(self.N + 1, np.int64)
        np.add.at(ptr, self.eu + 1, 1)
        return np.cumsum(ptr), order


def path_nodes(pred_row: np.ndarray, src: int, dst: int) -> list[int]:
    """Node sequence src..dst from a scipy predecessor row (empty if unreachable)."""
    if src == dst:
        return [src]
    out = [dst]
    cur = dst
    while cur != src:
        cur = pred_row[cur]
        if cur < 0:
            return []
        out.append(int(cur))
    out.reverse()
    return out
