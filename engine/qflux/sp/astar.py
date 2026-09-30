"""Time-dependent A* (§7.11). Admissible heuristic: straight-line distance / max free-flow speed.

Incidents and congestion only ever increase edge times above t0 >= length / max speed, so the bound
never overestimates and A* returns the same cost as TD-Dijkstra (T35).
"""
from .td_dijkstra import EdgeClock, td_shortest_path


def td_astar(net, clock: EdgeClock, src: int, dst: int, t0: float, adjacency=None) -> dict:
    vmax = clock.lower_bound_speed_kmh()
    target = net.node_xy[dst]
    xy = net.node_xy

    def h(v: int) -> float:
        return float(net.dist_km(xy[v], target)) / vmax * 60.0

    return td_shortest_path(net, clock, src, dst, t0, h, adjacency)
