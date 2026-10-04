"""Exact O(1)-delta local search for static instances (D41).

Static = one traffic slot (CVRPLIB): every leg cost is a fixed matrix entry W[a, b] (the same value the
time-dependent kernel computes with interpolation weight 0), so a move's cost change needs only the arcs it
breaks and creates. The operators below visit candidate moves in exactly the same order as the generic
kernels in `localsearch.py` and accept with the same rule (new cost < old cost - EPS); after an accepted
move the touched routes' costs are recomputed by a full sum in route order, which gives the same values the
generic kernel stores. Result: the same local optimum, much faster (equivalence test in tests/engine).

2-opt reversal cost uses forward/backward prefix sums, so it is exact for asymmetric matrices too.
"""
import numpy as np
from numba import njit

EPS = 1e-10


def static_leg_matrix(ev) -> np.ndarray:
    """W[a, b] = weighted cost of leg a->b, computed with the same expression as split.leg at lam = 0."""
    T = ev.Ts[0]
    D = ev.Ds[0]
    E = ev.Es[0]
    C = T - ev.T0
    C = np.where(C < 0.0, 0.0, C)
    wv, rv = ev.wv, ev.rv
    return np.ascontiguousarray(wv[0] * T / rv[0] + wv[1] * D / rv[1] + wv[2] * C / rv[2] + wv[3] * E / rv[3])


@njit(cache=True)
def _full(W, R, r, k):
    """Route cost in route order (depot -> R[r, :k] -> depot), the same summation order as route_cost_arr."""
    if k == 0:
        return 0.0
    total = 0.0
    prev = 0
    for p in range(k):
        c = R[r, p]
        total += W[prev, c]
        prev = c
    total += W[prev, 0]
    return total


@njit(cache=True)
def _node(R, r, k, p):
    """Node at route position p, with the depot at p = -1 and p = k."""
    if p < 0 or p >= k:
        return 0
    return R[r, p]


@njit(cache=True)
def _two_opt_s(W, R, L, cost, buf):
    improved = False
    for r in range(R.shape[0]):
        k = L[r]
        again = True
        while again:
            again = False
            # prefix sums of forward and backward arc costs along the route
            fwd = np.zeros(k + 1)
            bwd = np.zeros(k + 1)
            for p in range(k - 1):
                fwd[p + 1] = fwd[p] + W[R[r, p], R[r, p + 1]]
                bwd[p + 1] = bwd[p] + W[R[r, p + 1], R[r, p]]
            for i in range(k - 1):
                a = _node(R, r, k, i - 1)
                si = R[r, i]
                for j in range(i + 1, k):
                    sj = R[r, j]
                    b = _node(R, r, k, j + 1)
                    delta = (W[a, sj] + (bwd[j] - bwd[i]) + W[si, b]) - (W[a, si] + (fwd[j] - fwd[i]) + W[sj, b])
                    if cost[r] + delta < cost[r] - EPS:
                        for p in range(j - i + 1):
                            buf[p] = R[r, j - p]
                        for p in range(j - i + 1):
                            R[r, i + p] = buf[p]
                        cost[r] = _full(W, R, r, k)
                        improved = True
                        again = True
                        break
                if again:
                    break
    return improved


@njit(cache=True)
def _or_opt_s(W, R, L, cost, buf):
    improved = False
    for r in range(R.shape[0]):
        k = L[r]
        again = True
        while again:
            again = False
            for s in range(1, 4):
                if s >= k:
                    break
                for i in range(k - s + 1):
                    a = _node(R, r, k, i - 1)
                    b = _node(R, r, k, i + s)
                    f = R[r, i]
                    e = R[r, i + s - 1]
                    rem = W[a, b] - W[a, f] - W[e, b]
                    q = k - s
                    for pos in range(q + 1):
                        if pos == i:
                            continue
                        # neighbours in the route without the segment: tmp[p] = R[p] (p < i) else R[p + s]
                        if pos == 0:
                            x = 0
                        else:
                            x = R[r, pos - 1] if pos - 1 < i else R[r, pos - 1 + s]
                        if pos == q:
                            y = 0
                        else:
                            y = R[r, pos] if pos < i else R[r, pos + s]
                        delta = rem + (W[x, f] + W[e, y] - W[x, y])
                        if cost[r] + delta < cost[r] - EPS:
                            # build the new route exactly as the generic kernel does
                            o = 0
                            for p in range(k):
                                if p < i or p >= i + s:
                                    buf[o] = R[r, p]
                                    o += 1
                            seg0 = i
                            tmp_len = o
                            new = np.empty(k, np.int64)
                            o = 0
                            for p in range(pos):
                                new[o] = buf[p]
                                o += 1
                            for p in range(s):
                                new[o] = R[r, seg0 + p]
                                o += 1
                            for p in range(pos, tmp_len):
                                new[o] = buf[p]
                                o += 1
                            for p in range(k):
                                R[r, p] = new[p]
                            cost[r] = _full(W, R, r, k)
                            improved = True
                            again = True
                            break
                    if again:
                        break
                if again:
                    break
    return improved


@njit(cache=True)
def _relocate_s(W, R, L, cost, loads, demand, Q):
    m = R.shape[0]
    for r1 in range(m):
        k1 = L[r1]
        for i in range(k1):
            c = R[r1, i]
            a = _node(R, r1, k1, i - 1)
            b = _node(R, r1, k1, i + 1)
            q = k1 - 1
            c1 = cost[r1] + (W[a, b] - W[a, c] - W[c, b]) if q > 0 else 0.0
            for r2 in range(m):
                if r2 == r1 or L[r2] == 0 or loads[r2] + demand[c] > Q:
                    continue
                k2 = L[r2]
                for pos in range(k2 + 1):
                    x = _node(R, r2, k2, pos - 1)
                    y = _node(R, r2, k2, pos)
                    c2 = cost[r2] + (W[x, c] + W[c, y] - W[x, y])
                    if c1 + c2 < cost[r1] + cost[r2] - EPS:
                        for p in range(k2, pos, -1):
                            R[r2, p] = R[r2, p - 1]
                        R[r2, pos] = c
                        L[r2] = k2 + 1
                        for p in range(i, q):
                            R[r1, p] = R[r1, p + 1]
                        L[r1] = q
                        cost[r1] = _full(W, R, r1, q) if q > 0 else 0.0
                        cost[r2] = _full(W, R, r2, k2 + 1)
                        loads[r1] -= demand[c]
                        loads[r2] += demand[c]
                        return True
    return False


@njit(cache=True)
def _swap_s(W, R, L, cost, loads, demand, Q):
    m = R.shape[0]
    for r1 in range(m):
        k1 = L[r1]
        for r2 in range(r1 + 1, m):
            k2 = L[r2]
            for i in range(k1):
                a = R[r1, i]
                p1 = _node(R, r1, k1, i - 1)
                n1 = _node(R, r1, k1, i + 1)
                for j in range(k2):
                    b = R[r2, j]
                    if loads[r1] - demand[a] + demand[b] > Q or loads[r2] - demand[b] + demand[a] > Q:
                        continue
                    p2 = _node(R, r2, k2, j - 1)
                    n2 = _node(R, r2, k2, j + 1)
                    c1 = cost[r1] + (W[p1, b] + W[b, n1] - W[p1, a] - W[a, n1])
                    c2 = cost[r2] + (W[p2, a] + W[a, n2] - W[p2, b] - W[b, n2])
                    if c1 + c2 < cost[r1] + cost[r2] - EPS:
                        R[r1, i] = b
                        R[r2, j] = a
                        cost[r1] = _full(W, R, r1, k1)
                        cost[r2] = _full(W, R, r2, k2)
                        loads[r1] += demand[b] - demand[a]
                        loads[r2] += demand[a] - demand[b]
                        return True
    return False


@njit(cache=True)
def local_search_static(R, L, loads, demand, Q, W, ops, max_rounds, inner_cap):
    """Same round structure as localsearch.local_search. Returns (route costs, improved?)."""
    m, width = R.shape
    buf = np.empty(width + 1, np.int64)
    cost = np.zeros(m)
    for r in range(m):
        cost[r] = _full(W, R, r, L[r])
    any_improved = False
    for _ in range(max_rounds):
        improved = False
        if ops[0] and _two_opt_s(W, R, L, cost, buf):
            improved = True
        if ops[1] and _or_opt_s(W, R, L, cost, buf):
            improved = True
        if ops[2]:
            k = 0
            while k < inner_cap and _relocate_s(W, R, L, cost, loads, demand, Q):
                improved = True
                k += 1
        if ops[3]:
            k = 0
            while k < inner_cap and _swap_s(W, R, L, cost, loads, demand, Q):
                improved = True
                k += 1
        if improved:
            any_improved = True
        else:
            break
    return cost, any_improved
