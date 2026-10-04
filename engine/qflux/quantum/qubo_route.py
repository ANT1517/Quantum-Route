"""QUBO for ordering one route's stops (§3.8, §7.7.2). Binary x[i,p]: customer i at position p."""
from collections import defaultdict

import numpy as np


def build_route_qubo(route, dist, A=None) -> dict:
    m = len(route)
    nodes = [0] + list(route)
    idx = lambda i, p: i * m + p  # noqa: E731
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
                    a, b = sorted((idx(i, p), idx(j, p + 1)))
                    Q[(a, b)] += dist[ci, cj]
    for i in range(m):                                   # each customer exactly one position
        for p in range(m):
            Q[(idx(i, p), idx(i, p))] -= A
        for p1 in range(m):
            for p2 in range(p1 + 1, m):
                Q[(idx(i, p1), idx(i, p2))] += 2 * A
    for p in range(m):                                   # each position exactly one customer
        for i in range(m):
            Q[(idx(i, p), idx(i, p))] -= A
        for i1 in range(m):
            for i2 in range(i1 + 1, m):
                Q[(idx(i1, p), idx(i2, p))] += 2 * A
    return dict(Q)


def qubo_matrix(Q: dict, nvars: int) -> np.ndarray:
    M = np.zeros((nvars, nvars))
    for (a, b), v in Q.items():
        M[a, b] += v
    return M


def decode(sample: dict, route) -> list[int] | None:
    """Order from a sample, or None if it violates the one-hot constraints."""
    m = len(route)
    order = []
    for p in range(m):
        hits = [i for i in range(m) if sample.get(i * m + p, 0) == 1]
        if len(hits) != 1:
            return None
        order.append(hits[0])
    if sorted(order) != list(range(m)):
        return None
    return [route[i] for i in order]


def tour_cost(order, dist) -> float:
    seq = [0] + list(order) + [0]
    return float(sum(dist[a, b] for a, b in zip(seq[:-1], seq[1:])))
