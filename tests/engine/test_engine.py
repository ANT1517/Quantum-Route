"""Engine tests T01–T07, T10, T11, T28–T31 (§10.1)."""
import itertools

import numpy as np
import pytest

from qflux.algos.heldkarp import held_karp_tour
from qflux.algos.qpso import BASE_QPSO, QPSO, qpso_positions
from qflux.algos.registry import get_optimizer
from qflux.algos.tunneling import tunnel
from qflux.bench.loader import load_instance
from qflux.core.encoding import encode_perm, spv_decode
from qflux.core.evaluate import Evaluator
from qflux.core.feasibility import check
from qflux.core.localsearch import improve_solution
from qflux.core.split import extract_routes, split_static
from qflux.quantum.backends import solve_route_order
from qflux.quantum.qubo_route import build_route_qubo, decode, tour_cost
from qflux.rng import make_rng
from qflux.types import Weights

from ..fixtures.td_fixture import td_instance

DIST_W = Weights(wT=0.0, wD=1.0)
TD_W = Weights(wT=0.5, wD=0.2, wC=0.2, wE=0.1)


@pytest.fixture(scope="module")
def a32():
    return load_instance("A-n32-k5")


@pytest.fixture(scope="module", params=["static", "td"])
def ev(request, a32):
    if request.param == "static":
        return Evaluator(a32, DIST_W)
    return Evaluator(td_instance(), TD_W)


def test_t01_encode_decode_roundtrip():
    rng = make_rng(0)
    for _ in range(1000):
        perm = rng.permutation(50) + 1
        assert np.array_equal(spv_decode(encode_perm(perm, rng)), perm)


def test_t02_split_valid(ev):
    rng = make_rng(1)
    inst = ev.inst
    for _ in range(50):
        perm = spv_decode(rng.random(inst.n))
        cost, pred = ev._split(perm)
        routes = extract_routes(perm, pred)
        assert sorted(c for r in routes for c in r) == list(range(1, inst.n + 1))
        assert all(inst.demand[r].sum() <= inst.Q for r in routes)
        assert sum(ev.route_cost(r) for r in routes) == pytest.approx(cost)


def test_t03_split_brute_force():
    """Split = best partition of a 5-customer tour by brute force over all cut sets."""
    rng = make_rng(3)
    coords = rng.uniform(0, 100, (6, 2))
    C = np.sqrt(((coords[:, None] - coords[None]) ** 2).sum(-1))
    demand = np.array([0, 4, 3, 5, 2, 6], float)
    Q = 9.0
    perm = np.array([3, 1, 5, 2, 4])
    best = np.inf
    for cuts in itertools.product([0, 1], repeat=4):
        routes, cur = [], [perm[0]]
        for k, c in enumerate(cuts):
            if c:
                routes.append(cur); cur = []
            cur.append(perm[k + 1])
        routes.append(cur)
        if any(demand[r].sum() > Q for r in routes):
            continue
        cost = sum(C[0, r[0]] + sum(C[a, b] for a, b in zip(r[:-1], r[1:])) + C[r[-1], 0] for r in routes)
        best = min(best, cost)
    cost, _ = split_static(perm, demand, Q, C)
    assert cost == pytest.approx(best)


def test_t04_local_search_never_worse(ev):
    rng = make_rng(4)
    for _ in range(10):
        sol = ev.solution(rng.permutation(ev.inst.n) + 1)
        new = improve_solution(sol, ev)
        assert new.F <= sol.F + 1e-9
        assert all(ev.inst.demand[r].sum() <= ev.inst.Q for r in new.routes)
        assert check(ev.inst, new, ev)[0]


@pytest.mark.parametrize("algo", ["qpso", "pso", "ga", "sa"])
def test_t05_same_seed_same_result(a32, algo):
    params = {"qubo_slot": {"enabled": False}} if algo == "qpso" else {}
    out = []
    for _ in range(2):
        e = Evaluator(a32, DIST_W)
        sol, _ = get_optimizer(algo, dict(params)).run(e, 2000, None, make_rng(5))
        out.append((sol.F, sol.routes))
    assert out[0] == out[1]


def test_t06_qpso_improves(ev):
    sol, curve = QPSO(**BASE_QPSO).run(ev, 100 * 40, None, make_rng(6))
    assert curve[-1][1] <= curve[0][1] and sol.F <= curve[0][1] + 1e-9
    assert check(ev.inst, sol, ev)[0]


def test_t07_checker_detects_corruption(a32):
    e = Evaluator(a32, DIST_W)
    sol = e.solution(np.arange(1, a32.n + 1))
    dup = e.solution(np.arange(1, a32.n + 1)); dup.routes[0] = dup.routes[0] + [dup.routes[1][0]]
    miss = e.solution(np.arange(1, a32.n + 1)); miss.routes[0] = miss.routes[0][1:]
    over = e.solution(np.arange(1, a32.n + 1)); over.routes = [sum(over.routes, [])]; over.n_vehicles = 1
    assert check(a32, sol, e)[0]
    for bad, word in ((dup, "served"), (miss, "not served"), (over, "load")):
        ok, errs = check(a32, bad)
        assert not ok and any(word in m for m in errs), errs


def test_t10_held_karp_equals_brute():
    rng = make_rng(10)
    pts = rng.uniform(0, 100, (8, 2))
    dist = np.sqrt(((pts[:, None] - pts[None]) ** 2).sum(-1))
    route = list(range(1, 8))
    hk = held_karp_tour(route, dist)
    brute = min(itertools.permutations(route), key=lambda p: tour_cost(p, dist))
    assert tour_cost(hk, dist) == pytest.approx(tour_cost(brute, dist))


def test_t11_heuristic_not_below_milp():
    from qflux.algos.milp import solve_milp
    inst = load_instance("P-n16-k8")
    res = solve_milp(inst, time_limit_s=120)
    e = Evaluator(inst, DIST_W)
    sol, _ = get_optimizer("sa").run(e, 6000, None, make_rng(11))
    assert sol.D >= res["objective"] - 1e-6
    if res["optimal"]:
        assert res["objective"] == pytest.approx(inst.bks, rel=1e-6)


def test_t28_flags_change_behaviour(a32):
    rng = make_rng(28)
    X, P = rng.random((6, 10)), rng.random((6, 10))
    fP = rng.random(6)
    G = P[np.argmin(fP)]
    a = qpso_positions(X, P, fP, G, np.full(6, 0.7), "rank", make_rng(1))
    b = qpso_positions(X, P, fP, G, np.full(6, 0.7), "uniform", make_rng(1))
    assert not np.allclose(a, b)
    q = QPSO(alpha_mode="adaptive")
    al = q.alpha(np.array([1.0, 2.0, 3.0]), 0, 10)
    assert al[0] == pytest.approx(q.p["alpha_min"]) and al[-1] == pytest.approx(q.p["alpha_max"], rel=1e-6)
    lin = QPSO(alpha_mode="linear").alpha(np.zeros(3), 5, 10)
    assert np.allclose(lin, 0.75)
    s1 = QPSO(init="sobol").init_positions(8, 5, make_rng(2), None)
    s2 = QPSO(init="uniform").init_positions(8, 5, make_rng(2), None)
    assert not np.allclose(s1, s2)


def test_t29_tunneling_elitism(a32):
    e = Evaluator(a32, DIST_W)
    rng = make_rng(29)
    perm = rng.permutation(a32.n) + 1
    f0 = e.fitness_perm(perm)
    kinds = set()
    for _ in range(30):
        cand, f, kind = tunnel(perm, f0, e, rng)
        kinds.add(kind)
        if kind == "improve":
            assert f < f0
    # inside QPSO: G never worsens and accepted worse moves only overwrite the worst particle
    q = QPSO(qubo_slot={"enabled": False}, tunneling={"enabled": True, "stagnation": 1})
    sol, curve = q.run(Evaluator(a32, DIST_W), 3000, None, make_rng(3))
    bests = [f for _, f in curve]
    assert all(b2 <= b1 + 1e-12 for b1, b2 in zip(bests, bests[1:]))
    assert sol.meta["tunnel_events"]


def test_t30_qubo_brute_equals_itertools():
    rng = make_rng(30)
    pts = rng.uniform(0, 10, (6, 2))
    dist = np.sqrt(((pts[:, None] - pts[None]) ** 2).sum(-1))
    route = [1, 2, 3, 4, 5]
    out = solve_route_order(route, dist, "brute")
    best = min(itertools.permutations(route), key=lambda p: tour_cost(p, dist))
    assert out["cost"] == pytest.approx(tour_cost(best, dist)) and out["feasible"]
    # the QUBO energy of the optimal assignment equals tour cost minus the dropped constant 2*A*m
    Q = build_route_qubo(route, dist, A=100.0)
    m = len(route)
    x = {i * m + p: 1 for p, c in enumerate(best) for i in [route.index(c)]}
    E = sum(v * x.get(a, 0) * x.get(b, 0) for (a, b), v in Q.items())
    assert E + 2 * 100.0 * m == pytest.approx(tour_cost(best, dist))


def test_t31_infeasible_sample_keeps_route(monkeypatch):
    import qflux.quantum.backends as be
    monkeypatch.setattr(be, "_neal", lambda route, dist, *a, **k: (None, 0.0))
    dist = np.ones((4, 4))
    out = be.solve_route_order([1, 2, 3], dist, "neal")
    assert out["order"] == [1, 2, 3] and out["feasible"] is False
    assert decode({0: 1, 1: 1}, [1, 2]) is None
