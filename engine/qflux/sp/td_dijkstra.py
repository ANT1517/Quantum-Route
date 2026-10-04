"""Time-dependent Dijkstra (exact under FIFO) on RoadNet arrays (§7.11)."""
import heapq

import numpy as np

from qflux.traffic import events
from qflux.traffic.emissions import edge_co2_kg
from qflux.traffic.profiles import SLOT_CENTERS, slot_weights
from qflux.traffic.roadnet import RoadNet
from qflux.traffic.td_matrix import edge_times


class EdgeClock:
    """edge_time(edges, t): minutes to traverse `edges` entering at time t.

    Background traffic is interpolated between slot centres (continuous in t); incidents multiply the
    edge time exactly inside their time window (BPR is linear in t0, so this equals scaling t0).
    """

    def __init__(self, net: RoadNet, incidents=None, static: bool = False, centers=SLOT_CENTERS):
        self.net, self.static, self.centers = net, static, centers
        self.incidents = list(incidents or [])
        self._inc_edges = [(inc, events.affected_edges(net, inc)) for inc in self.incidents]
        if static:
            self.slot_times = net.t0_min[None, :]
        else:
            self.slot_times = np.stack([edge_times(net, c) for c in centers])
        self._mult_cache: dict[tuple, np.ndarray] = {}

    def _mult(self, t: float):
        key = tuple(i for i, (inc, _) in enumerate(self._inc_edges) if events.is_active(inc, t))
        if not key:
            return None
        if key not in self._mult_cache:
            m = np.ones(self.net.E)
            for i in key:
                inc, e = self._inc_edges[i]
                m[e] *= inc.factor
            self._mult_cache[key] = m
        return self._mult_cache[key]

    def __call__(self, edges: np.ndarray, t: float) -> np.ndarray:
        if self.static:
            base = self.slot_times[0, edges]
        else:
            s, s1, lam = slot_weights(t, self.centers)
            base = (1 - lam) * self.slot_times[s, edges] + lam * self.slot_times[s1, edges]
        m = self._mult(t)
        return base if m is None else base * m[edges]

    def lower_bound_speed_kmh(self) -> float:
        return float((self.net.length_km / self.net.t0_min * 60.0).max())


def td_shortest_path(net: RoadNet, clock: EdgeClock, src: int, dst: int, t0: float, heuristic=None,
                     adjacency=None) -> dict:
    """Label-setting search on arrival time. heuristic(node) -> lower bound on remaining minutes (A*)."""
    ptr, order = adjacency if adjacency is not None else net.adjacency()
    h = heuristic or (lambda v: 0.0)
    best = {src: t0}
    prev: dict[int, int] = {}          # node -> edge index used to reach it
    pq = [(t0 + h(src), t0, src)]
    settled = 0
    done = set()
    while pq:
        _, t, u = heapq.heappop(pq)
        if u in done:
            continue
        done.add(u)
        settled += 1
        if u == dst:
            break
        out = order[ptr[u]:ptr[u + 1]]
        if len(out) == 0:
            continue
        ta = t + clock(out, t)
        for e, a in zip(out, ta):
            v = int(net.ev[e])
            if a < best.get(v, np.inf):
                best[v] = a
                prev[v] = int(e)
                heapq.heappush(pq, (a + h(v), a, v))
    if dst not in done:
        return dict(found=False, settled=settled)
    edges = []
    v = dst
    while v != src:
        e = prev[v]
        edges.append(e)
        v = int(net.eu[e])
    edges.reverse()
    edges = np.array(edges, np.int64)
    nodes = [src] + [int(net.ev[e]) for e in edges]
    # distance / CO2 along the path at the times each edge is entered
    t, co2 = t0, 0.0
    times = [0.0]                                   # minutes after departure at each node of the path
    for e in edges:
        dt = float(clock(np.array([e]), t)[0])
        co2 += float(edge_co2_kg(net.length_km[e], dt))
        t += dt
        times.append(t - t0)
    return dict(found=True, nodes=nodes, edges=edges, eta_min=best[dst] - t0, settled=settled, times=times,
                distance_km=float(net.length_km[edges].sum()), co2_kg=co2)


def td_dijkstra(net: RoadNet, clock: EdgeClock, src: int, dst: int, t0: float, adjacency=None) -> dict:
    return td_shortest_path(net, clock, src, dst, t0, None, adjacency)
