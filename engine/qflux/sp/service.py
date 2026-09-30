"""POST /shortest-path handler logic (§5.4): {path_geometry, eta_min, cost, runtime_s, gap_pct?}."""
import time

from qflux.traffic import events
from qflux.traffic.roadnet import RoadNet

from .astar import td_astar
from .td_dijkstra import EdgeClock, td_dijkstra


class NoPath(LookupError):
    """Maps to HTTP 404 (no path)."""


def resolve_node(net: RoadNet, p) -> int:
    """A node index, or a [lat, lon] / [y, x] point snapped to the nearest node."""
    if isinstance(p, (list, tuple)):
        return net.nearest_node(p)
    p = int(p)
    if not 0 <= p < net.N:
        raise NoPath(f"node {p} not in graph")
    return p


def shortest_path_request(net: RoadNet, req: dict, clock: EdgeClock | None = None) -> dict:
    src, dst = resolve_node(net, req["source"]), resolve_node(net, req["target"])
    t0 = float(req.get("depart_min", 1050))
    algo = req.get("algorithm", "dijkstra")
    if clock is None:
        incs = [events.from_spec(d) for d in req.get("incidents", [])]
        clock = EdgeClock(net, incs)
    fn = {"dijkstra": td_dijkstra, "astar": td_astar}.get(algo)
    if fn is None:
        raise NotImplementedError(f"shortest-path algorithm {algo!r} (QPSO-SP is P1)")
    t = time.time()
    res = fn(net, clock, src, dst, t0)
    runtime = time.time() - t
    if not res["found"]:
        raise NoPath(f"no path from {src} to {dst}")
    geom = net.node_xy[res["nodes"]].round(6).tolist()
    return dict(path_geometry=geom, eta_min=round(res["eta_min"], 3), cost=round(res["eta_min"], 3),
                runtime_s=round(runtime, 4))
