"""Held-Karp exact DP for a single route (§7.9), O(m^2 2^m), m <= 12."""
import itertools


def held_karp_tour(route, dist, depot: int = 0) -> list[int]:
    stops = list(route)
    m = len(stops)
    if m <= 1:
        return stops
    if m > 12:
        raise ValueError("Held-Karp limited to 12 stops")
    dp = {(1 << k, k): (dist[depot, stops[k]], -1) for k in range(m)}
    for size in range(2, m + 1):
        for subset in itertools.combinations(range(m), size):
            mask = sum(1 << k for k in subset)
            for k in subset:
                pm = mask ^ (1 << k)
                dp[(mask, k)] = min(((dp[(pm, j)][0] + dist[stops[j], stops[k]], j) for j in subset if j != k),
                                    key=lambda x: x[0])
    full = (1 << m) - 1
    last = min(range(m), key=lambda k: dp[(full, k)][0] + dist[stops[k], depot])
    order, mask = [], full
    while last != -1:
        order.append(stops[last])
        _, prv = dp[(mask, last)]
        mask ^= 1 << last
        last = prv
    return order[::-1]
