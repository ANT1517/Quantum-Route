"""Static-proxy local search with time-dependent verification (D46), for Hyderabad / SynthCity instances.

Candidate moves are scored with O(1) deltas on a static proxy matrix (the weighted leg cost at the dispatch
slot, the same matrix the QUBO slot and OR-Tools use). Only a move the proxy says improves is re-evaluated
with the full time-dependent cost of the 1-2 routes it touches, and it is kept only if that true cost
improves (by more than EPS); otherwise the scan continues. Every accepted move strictly lowers the true
cost, so the result is never worse than the input and the search terminates. Capacity is checked exactly as
in the other kernels. Unlike D41 this is NOT move-for-move identical to the generic kernel (moves the proxy
does not see are skipped), which is why it is a separate decision.
"""
import numpy as np
from numba import njit

from .ls_static import _node
from .split import route_cost_arr

EPS = 1e-10


def proxy_matrix(ev) -> np.ndarray:
    """Weighted leg cost at the dispatch slot (tau0), cached on the evaluator."""
    W = getattr(ev, "_ls_proxy_W", None)
    if W is None:
        from qflux.algos.qpso import dispatch_cost_matrix
        W = np.ascontiguousarray(dispatch_cost_matrix(ev), dtype=np.float64)
        ev._ls_proxy_W = W
    return W


@njit(cache=True)
def _td(buf, k, A0, A1, A2, A3, A4, sv, tau0, wv, rv):
    if k == 0:
        return 0.0
    return route_cost_arr(buf, k, A0, A1, A2, A3, A4, sv, tau0, wv, rv)


@njit(cache=True)
def _two_opt_p(W, R, L, tc, buf, A0, A1, A2, A3, A4, sv, tau0, wv, rv):
    improved = False
    for r in range(R.shape[0]):
        k = L[r]
        again = True
        while again:
            again = False
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
                    if delta < -EPS:
                        for p in range(k):
                            buf[p] = R[r, p]
                        for p in range(j - i + 1):
                            buf[i + p] = R[r, j - p]
                        c = _td(buf, k, A0, A1, A2, A3, A4, sv, tau0, wv, rv)
                        if c < tc[r] - EPS:                     # verified on the true TD cost
                            for p in range(k):
                                R[r, p] = buf[p]
                            tc[r] = c
                            improved = True
                            again = True
                            break
                if again:
                    break
    return improved


@njit(cache=True)
def _or_opt_p(W, R, L, tc, buf, new, A0, A1, A2, A3, A4, sv, tau0, wv, rv):
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
                        x = 0 if pos == 0 else (R[r, pos - 1] if pos - 1 < i else R[r, pos - 1 + s])
                        y = 0 if pos == q else (R[r, pos] if pos < i else R[r, pos + s])
                        if rem + (W[x, f] + W[e, y] - W[x, y]) < -EPS:
                            o = 0
                            for p in range(k):
                                if p < i or p >= i + s:
                                    buf[o] = R[r, p]
                                    o += 1
                            o = 0
                            for p in range(pos):
                                new[o] = buf[p]
                                o += 1
                            for p in range(s):
                                new[o] = R[r, i + p]
                                o += 1
                            for p in range(pos, q):
                                new[o] = buf[p]
                                o += 1
                            c = _td(new, k, A0, A1, A2, A3, A4, sv, tau0, wv, rv)
                            if c < tc[r] - EPS:
                                for p in range(k):
                                    R[r, p] = new[p]
                                tc[r] = c
                                improved = True
                                again = True
                                break
                    if again:
                        break
                if again:
                    break
    return improved


@njit(cache=True)
def _relocate_p(W, R, L, tc, loads, demand, Q, buf, tmp, A0, A1, A2, A3, A4, sv, tau0, wv, rv):
    m = R.shape[0]
    for r1 in range(m):
        k1 = L[r1]
        for i in range(k1):
            c = R[r1, i]
            a = _node(R, r1, k1, i - 1)
            b = _node(R, r1, k1, i + 1)
            d1 = W[a, b] - W[a, c] - W[c, b]
            q = k1 - 1
            for r2 in range(m):
                if r2 == r1 or L[r2] == 0 or loads[r2] + demand[c] > Q:
                    continue
                k2 = L[r2]
                for pos in range(k2 + 1):
                    x = _node(R, r2, k2, pos - 1)
                    y = _node(R, r2, k2, pos)
                    if d1 + (W[x, c] + W[c, y] - W[x, y]) < -EPS:
                        o = 0
                        for p in range(k1):
                            if p != i:
                                tmp[o] = R[r1, p]
                                o += 1
                        o = 0
                        for p in range(pos):
                            buf[o] = R[r2, p]
                            o += 1
                        buf[o] = c
                        o += 1
                        for p in range(pos, k2):
                            buf[o] = R[r2, p]
                            o += 1
                        c1 = _td(tmp, q, A0, A1, A2, A3, A4, sv, tau0, wv, rv)
                        c2 = _td(buf, k2 + 1, A0, A1, A2, A3, A4, sv, tau0, wv, rv)
                        if c1 + c2 < tc[r1] + tc[r2] - EPS:
                            for p in range(k2 + 1):
                                R[r2, p] = buf[p]
                            L[r2] = k2 + 1
                            for p in range(q):
                                R[r1, p] = tmp[p]
                            L[r1] = q
                            tc[r1] = c1
                            tc[r2] = c2
                            loads[r1] -= demand[c]
                            loads[r2] += demand[c]
                            return True
    return False


@njit(cache=True)
def _swap_p(W, R, L, tc, loads, demand, Q, buf, tmp, A0, A1, A2, A3, A4, sv, tau0, wv, rv):
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
                    d = (W[p1, b] + W[b, n1] - W[p1, a] - W[a, n1]) + (W[p2, a] + W[a, n2] - W[p2, b] - W[b, n2])
                    if d < -EPS:
                        for p in range(k1):
                            buf[p] = R[r1, p]
                        buf[i] = b
                        for p in range(k2):
                            tmp[p] = R[r2, p]
                        tmp[j] = a
                        c1 = _td(buf, k1, A0, A1, A2, A3, A4, sv, tau0, wv, rv)
                        c2 = _td(tmp, k2, A0, A1, A2, A3, A4, sv, tau0, wv, rv)
                        if c1 + c2 < tc[r1] + tc[r2] - EPS:
                            R[r1, i] = b
                            R[r2, j] = a
                            tc[r1] = c1
                            tc[r2] = c2
                            loads[r1] += demand[b] - demand[a]
                            loads[r2] += demand[a] - demand[b]
                            return True
    return False


@njit(cache=True)
def local_search_td_proxy(R, L, loads, demand, Q, W, A0, A1, A2, A3, A4, sv, tau0, wv, rv, ops, max_rounds, inner_cap):
    """Same round structure as the other kernels. Returns (true TD route costs, improved?)."""
    m, width = R.shape
    buf = np.empty(width + 1, np.int64)
    tmp = np.empty(width + 1, np.int64)
    new = np.empty(width + 1, np.int64)
    tc = np.zeros(m)
    for r in range(m):
        tc[r] = _td(R[r], L[r], A0, A1, A2, A3, A4, sv, tau0, wv, rv)
    any_improved = False
    for _ in range(max_rounds):
        improved = False
        if ops[0] and _two_opt_p(W, R, L, tc, buf, A0, A1, A2, A3, A4, sv, tau0, wv, rv):
            improved = True
        if ops[1] and _or_opt_p(W, R, L, tc, buf, new, A0, A1, A2, A3, A4, sv, tau0, wv, rv):
            improved = True
        if ops[2]:
            k = 0
            while k < inner_cap and _relocate_p(W, R, L, tc, loads, demand, Q, buf, tmp, A0, A1, A2, A3, A4, sv,
                                                tau0, wv, rv):
                improved = True
                k += 1
        if ops[3]:
            k = 0
            while k < inner_cap and _swap_p(W, R, L, tc, loads, demand, Q, buf, tmp, A0, A1, A2, A3, A4, sv,
                                            tau0, wv, rv):
                improved = True
                k += 1
        if improved:
            any_improved = True
        else:
            break
    return tc, any_improved
