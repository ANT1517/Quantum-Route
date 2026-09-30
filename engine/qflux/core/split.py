"""Prins Split (§7.3) and the Numba leg/route kernels shared by Split, local search and evaluation.

All costs follow §3.3/§3.4: per route the clock starts at tau0; departing stop a at time t costs
w_T*T/T_ref + w_D*D/D_ref + w_C*max(T - T0, 0)/C_ref + w_E*E/E_ref with T, D, E linearly interpolated
between slot centres (wrapping at midnight). Static instances use a single "slot" (T = D, E = 0).

`A` below is the packed tuple (centers, Ts, Ds, Es, T0, service, tau0, wv, rv) built by the Evaluator.
"""
import numpy as np
from numba import njit

DAY = 1440.0


@njit(cache=True)
def interp(centers, t):
    S = centers.shape[0]
    if S == 1:
        return 0, 0, 0.0
    t = t % DAY
    if t < centers[0] or t >= centers[S - 1]:
        span = centers[0] + DAY - centers[S - 1]
        return S - 1, 0, ((t - centers[S - 1]) % DAY) / span
    s = 0
    while centers[s + 1] <= t:
        s += 1
    return s, s + 1, (t - centers[s]) / (centers[s + 1] - centers[s])


@njit(cache=True)
def leg(a, b, t, centers, Ts, Ds, Es, T0, wv, rv):
    """(weighted cost, T, D, C, E) of leg a->b departing at t."""
    s, s1, lam = interp(centers, t)
    T = (1.0 - lam) * Ts[s, a, b] + lam * Ts[s1, a, b]
    D = (1.0 - lam) * Ds[s, a, b] + lam * Ds[s1, a, b]
    E = (1.0 - lam) * Es[s, a, b] + lam * Es[s1, a, b]
    C = T - T0[a, b]
    if C < 0.0:
        C = 0.0
    cost = wv[0] * T / rv[0] + wv[1] * D / rv[1] + wv[2] * C / rv[2] + wv[3] * E / rv[3]
    return cost, T, D, C, E


@njit(cache=True)
def route_cost_arr(seq, k, centers, Ts, Ds, Es, T0, service, tau0, wv, rv):
    """Weighted cost of depot -> seq[:k] -> depot starting at tau0."""
    t = tau0
    prev = 0
    total = 0.0
    for p in range(k):
        c = seq[p]
        td = t + service[prev]
        cost, T, D, C, E = leg(prev, c, td, centers, Ts, Ds, Es, T0, wv, rv)
        total += cost
        t = td + T
        prev = c
    if k > 0:
        cost, T, D, C, E = leg(prev, 0, t + service[prev], centers, Ts, Ds, Es, T0, wv, rv)
        total += cost
    return total


@njit(cache=True)
def route_components(seq, k, centers, Ts, Ds, Es, T0, service, tau0, wv, rv):
    """(T, D, C, E) totals of one route."""
    t = tau0
    prev = 0
    sT = sD = sC = sE = 0.0
    for p in range(k + 1):
        c = seq[p] if p < k else 0
        td = t + service[prev]
        cost, T, D, C, E = leg(prev, c, td, centers, Ts, Ds, Es, T0, wv, rv)
        sT += T; sD += D; sC += C; sE += E
        t = td + T
        prev = c
    return sT, sD, sC, sE


@njit(cache=True)
def split_static(perm, demand, Q, C):
    """Static Prins Split (§7.3.1): optimal partition of the giant tour under arc costs C."""
    n = perm.shape[0]
    V = np.full(n + 1, np.inf)
    V[0] = 0.0
    pred = np.full(n + 1, -1, np.int64)
    for i in range(n):
        load = 0.0
        cost = 0.0
        for j in range(i, n):
            cj = perm[j]
            load += demand[cj]
            if load > Q:
                break
            if j == i:
                cost = C[0, cj]
            else:
                cost += C[perm[j - 1], cj]
            total = cost + C[cj, 0]
            if V[i] + total < V[j + 1]:
                V[j + 1] = V[i] + total
                pred[j + 1] = i
    return V[n], pred


@njit(cache=True)
def split_td(perm, demand, Q, centers, Ts, Ds, Es, T0, service, tau0, wv, rv):
    """Time-dependent Split (§7.3.2): per start i the clock resets to tau0."""
    n = perm.shape[0]
    V = np.full(n + 1, np.inf)
    V[0] = 0.0
    pred = np.full(n + 1, -1, np.int64)
    for i in range(n):
        if V[i] == np.inf:
            continue
        load = 0.0
        cost = 0.0
        t = tau0
        prev = 0
        for j in range(i, n):
            cj = perm[j]
            load += demand[cj]
            if load > Q:
                break
            td = t + service[prev]
            c, T, D, C, E = leg(prev, cj, td, centers, Ts, Ds, Es, T0, wv, rv)
            cost += c
            t = td + T
            prev = cj
            back, T2, D2, C2, E2 = leg(cj, 0, t + service[cj], centers, Ts, Ds, Es, T0, wv, rv)
            total = cost + back
            if V[i] + total < V[j + 1]:
                V[j + 1] = V[i] + total
                pred[j + 1] = i
    return V[n], pred


@njit(cache=True)
def count_routes(pred, n):
    m = 0
    j = n
    while j > 0:
        j = pred[j]
        m += 1
    return m


def extract_routes(perm, pred) -> list[list[int]]:
    routes = []
    j = len(perm)
    while j > 0:
        i = int(pred[j])
        routes.append([int(c) for c in perm[i:j]])
        j = i
    routes.reverse()
    return routes
