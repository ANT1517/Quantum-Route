"""Local search (§7.4): intra-route 2-opt and or-opt (segments 1–3); inter-route relocate and swap with
capacity checks; first improvement. Moves are scored with exact time-dependent route costs (not counted
as evaluations). The whole search runs in Numba.
"""
import numpy as np
from numba import njit

from qflux.types import Solution

from .split import route_cost_arr

EPS = 1e-10
OPS = ("2opt", "oropt", "relocate", "swap")


@njit(cache=True)
def _rc(buf, k, A0, A1, A2, A3, A4, sv, tau0, wv, rv):
    return route_cost_arr(buf, k, A0, A1, A2, A3, A4, sv, tau0, wv, rv)


@njit(cache=True)
def _two_opt(R, L, cost, buf, A0, A1, A2, A3, A4, sv, tau0, wv, rv):
    improved = False
    for r in range(R.shape[0]):
        k = L[r]
        again = True
        while again:
            again = False
            for i in range(k - 1):
                for j in range(i + 1, k):
                    for p in range(k):
                        buf[p] = R[r, p]
                    for p in range(j - i + 1):
                        buf[i + p] = R[r, j - p]
                    c = _rc(buf, k, A0, A1, A2, A3, A4, sv, tau0, wv, rv)
                    if c < cost[r] - EPS:
                        for p in range(k):
                            R[r, p] = buf[p]
                        cost[r] = c
                        improved = True
                        again = True
                        break
                if again:
                    break
    return improved


@njit(cache=True)
def _or_opt(R, L, cost, buf, tmp, A0, A1, A2, A3, A4, sv, tau0, wv, rv):
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
                    # route without segment [i, i+s)
                    q = 0
                    for p in range(k):
                        if p < i or p >= i + s:
                            tmp[q] = R[r, p]
                            q += 1
                    for pos in range(q + 1):
                        if pos == i:
                            continue
                        # insert segment at pos
                        o = 0
                        for p in range(pos):
                            buf[o] = tmp[p]; o += 1
                        for p in range(s):
                            buf[o] = R[r, i + p]; o += 1
                        for p in range(pos, q):
                            buf[o] = tmp[p]; o += 1
                        c = _rc(buf, k, A0, A1, A2, A3, A4, sv, tau0, wv, rv)
                        if c < cost[r] - EPS:
                            for p in range(k):
                                R[r, p] = buf[p]
                            cost[r] = c
                            improved = True
                            again = True
                            break
                    if again:
                        break
                if again:
                    break
    return improved


@njit(cache=True)
def _relocate(R, L, cost, loads, demand, Q, buf, tmp, A0, A1, A2, A3, A4, sv, tau0, wv, rv):
    m = R.shape[0]
    for r1 in range(m):
        for i in range(L[r1]):
            c = R[r1, i]
            # r1 without customer c
            q = 0
            for p in range(L[r1]):
                if p != i:
                    tmp[q] = R[r1, p]
                    q += 1
            c1 = _rc(tmp, q, A0, A1, A2, A3, A4, sv, tau0, wv, rv) if q > 0 else 0.0
            for r2 in range(m):
                if r2 == r1 or L[r2] == 0 or loads[r2] + demand[c] > Q:
                    continue
                k2 = L[r2]
                for pos in range(k2 + 1):
                    o = 0
                    for p in range(pos):
                        buf[o] = R[r2, p]; o += 1
                    buf[o] = c; o += 1
                    for p in range(pos, k2):
                        buf[o] = R[r2, p]; o += 1
                    c2 = _rc(buf, k2 + 1, A0, A1, A2, A3, A4, sv, tau0, wv, rv)
                    if c1 + c2 < cost[r1] + cost[r2] - EPS:
                        for p in range(k2 + 1):
                            R[r2, p] = buf[p]
                        L[r2] = k2 + 1
                        for p in range(q):
                            R[r1, p] = tmp[p]
                        L[r1] = q
                        cost[r1] = c1
                        cost[r2] = c2
                        loads[r1] -= demand[c]
                        loads[r2] += demand[c]
                        return True
    return False


@njit(cache=True)
def _swap(R, L, cost, loads, demand, Q, buf, tmp, A0, A1, A2, A3, A4, sv, tau0, wv, rv):
    m = R.shape[0]
    for r1 in range(m):
        for r2 in range(r1 + 1, m):
            for i in range(L[r1]):
                a = R[r1, i]
                for j in range(L[r2]):
                    b = R[r2, j]
                    if loads[r1] - demand[a] + demand[b] > Q or loads[r2] - demand[b] + demand[a] > Q:
                        continue
                    for p in range(L[r1]):
                        buf[p] = R[r1, p]
                    buf[i] = b
                    for p in range(L[r2]):
                        tmp[p] = R[r2, p]
                    tmp[j] = a
                    c1 = _rc(buf, L[r1], A0, A1, A2, A3, A4, sv, tau0, wv, rv)
                    c2 = _rc(tmp, L[r2], A0, A1, A2, A3, A4, sv, tau0, wv, rv)
                    if c1 + c2 < cost[r1] + cost[r2] - EPS:
                        R[r1, i] = b
                        R[r2, j] = a
                        cost[r1] = c1
                        cost[r2] = c2
                        loads[r1] += demand[b] - demand[a]
                        loads[r2] += demand[a] - demand[b]
                        return True
    return False


@njit(cache=True)
def local_search(R, L, loads, demand, Q, A0, A1, A2, A3, A4, sv, tau0, wv, rv, ops, max_rounds):
    m, width = R.shape
    buf = np.empty(width + 1, np.int64)
    tmp = np.empty(width + 1, np.int64)
    cost = np.zeros(m)
    for r in range(m):
        if L[r] > 0:
            cost[r] = _rc(R[r], L[r], A0, A1, A2, A3, A4, sv, tau0, wv, rv)
    for _ in range(max_rounds):
        improved = False
        if ops[0] and _two_opt(R, L, cost, buf, A0, A1, A2, A3, A4, sv, tau0, wv, rv):
            improved = True
        if ops[1] and _or_opt(R, L, cost, buf, tmp, A0, A1, A2, A3, A4, sv, tau0, wv, rv):
            improved = True
        if ops[2]:
            while _relocate(R, L, cost, loads, demand, Q, buf, tmp, A0, A1, A2, A3, A4, sv, tau0, wv, rv):
                improved = True
        if ops[3]:
            while _swap(R, L, cost, loads, demand, Q, buf, tmp, A0, A1, A2, A3, A4, sv, tau0, wv, rv):
                improved = True
        if not improved:
            break
    return cost


def improve_routes(routes, ev, ops=OPS, max_rounds: int = 50) -> list[list[int]]:
    routes = [list(r) for r in routes if r]
    if not routes:
        return routes
    width = ev.inst.n + 1
    m = len(routes)
    R = np.zeros((m, width), np.int64)
    L = np.zeros(m, np.int64)
    loads = np.zeros(m)
    for k, r in enumerate(routes):
        R[k, :len(r)] = r
        L[k] = len(r)
        loads[k] = ev.demand[r].sum()
    mask = np.array([op in ops for op in OPS])
    local_search(R, L, loads, ev.demand, ev.Q, ev.centers, ev.Ts, ev.Ds, ev.Es, ev.T0, ev.service, ev.tau0,
                 ev.wv, ev.rv, mask, max_rounds)
    return [R[k, :L[k]].tolist() for k in range(m) if L[k] > 0]


def improve_solution(sol: Solution, ev, ops=OPS) -> Solution:
    """Returns a solution whose F is never higher than the input's (T04)."""
    new = ev.solution_from_routes(improve_routes(sol.routes, ev, ops), meta=sol.meta)
    return new if new.F <= sol.F + 1e-12 else sol
