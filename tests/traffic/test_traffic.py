"""Traffic tests T12–T17 (§10.1). SynthCity always; Hyderabad when its cache exists."""
import time

import networkx as nx
import numpy as np
import pytest

from qflux import api
from qflux.sp.astar import td_astar
from qflux.sp.td_dijkstra import EdgeClock, td_dijkstra
from qflux.traffic.bpr import bpr_time, marginal_cost
from qflux.traffic.hyd_graph import ROADNET_NPZ
from qflux.traffic.profiles import ARTERIAL, LOAD_RATIO, SLOT_CENTERS, load_ratio
from qflux.traffic.synth_city import build_synth
from qflux.traffic.td_matrix import bundle_for

SYNTH = {"source": "synth", "n_customers": 40, "K": 8, "Q": 100, "tau0": 1050}
HYD = {"source": "hyderabad", "n_customers": 60}
has_hyd = pytest.mark.skipif(not ROADNET_NPZ.exists(), reason="Hyderabad cache missing (scripts/build_hyd.py)")


@pytest.fixture(scope="module")
def synth():
    inst = api.build_instance(SYNTH)
    return inst, bundle_for(inst)


@pytest.fixture(scope="module")
def hyd():
    inst = api.build_instance(HYD)
    return inst, bundle_for(inst)


def _specs():
    return [pytest.param("synth"), pytest.param("hyd", marks=has_hyd)]


@pytest.fixture(params=_specs())
def any_inst(request):
    return request.getfixturevalue(request.param)


# T12 --------------------------------------------------------------------------------------------
def test_t12_bpr_monotonic():
    v = np.linspace(0, 3000, 301)
    t = bpr_time(2.0, v, 1500.0)
    assert t[0] == pytest.approx(2.0)
    assert np.all(np.diff(t) > 0)
    mc = marginal_cost(2.0, v, 1500.0)
    assert np.all(mc >= t) and mc[0] == pytest.approx(2.0)


# T13 --------------------------------------------------------------------------------------------
def test_t13_reachability(any_inst):
    inst, b = any_inst
    m = inst.n + 1
    off = ~np.eye(m, dtype=bool)
    for s in range(len(b.slot_centers)):
        assert np.all(np.isfinite(b.T_slots[s][off])) and np.all(b.T_slots[s][off] > 0)
        for i in range(m):          # every stored path exists and connects the right nodes
            for j in (0, (i + 1) % m):
                if i != j:
                    e = b.path(s, i, j)
                    assert b.net.eu[e[0]] == b.terminals[i] and b.net.ev[e[-1]] == b.terminals[j]


# T14 --------------------------------------------------------------------------------------------
def test_t14_peak_multiplier():
    g = np.array([ARTERIAL])
    peak = bpr_time(1.0, load_ratio(1050, g) * 1.0, 1.0)[0]
    night = bpr_time(1.0, load_ratio(180, g) * 1.0, 1.0)[0]
    assert 1.7 <= peak <= 2.0
    assert night == pytest.approx(1.0, abs=0.01)
    assert LOAD_RATIO.shape == (len(SLOT_CENTERS), 3)


# T15 --------------------------------------------------------------------------------------------
def test_t15_fifo(any_inst):
    inst, b = any_inst
    rng = np.random.default_rng(0)
    grid = np.arange(0, 1440, 2.0)
    for _ in range(1000):
        i, j = rng.choice(inst.n + 1, 2, replace=False)
        arr = np.array([t + b.leg(i, j, t)[0] for t in grid])
        assert np.all(np.diff(arr) >= -1e-9), (i, j)


# T16 --------------------------------------------------------------------------------------------
def _path_change_share(b) -> float:
    s_night, s_peak = list(b.slot_centers).index(180.0), list(b.slot_centers).index(1050.0)
    m, changed, total = b.m, 0, 0
    for i in range(m):
        for j in range(m):
            if i != j:
                total += 1
                changed += not np.array_equal(b.path(s_night, i, j), b.path(s_peak, i, j))
    return changed / total


@has_hyd
def test_t16_time_dependence_matters(hyd):
    share = _path_change_share(hyd[1])
    print(f"T16 Hyderabad: {100 * share:.1f}% of pairs change path 03:00 -> 17:30")
    assert share >= 0.15


def test_t16_synth_reports(synth):
    print(f"T16 SynthCity: {100 * _path_change_share(synth[1]):.1f}% of pairs change path 03:00 -> 17:30")


# T17 --------------------------------------------------------------------------------------------
def test_t17_td_dijkstra_matches_networkx_static():
    net = build_synth(grid=12, seed=3)
    G = nx.DiGraph()
    for e in range(net.E):
        u, v, w = int(net.eu[e]), int(net.ev[e]), float(net.t0_min[e])
        if not G.has_edge(u, v) or G[u][v]["w"] > w:
            G.add_edge(u, v, w=w)
    clock = EdgeClock(net, static=True)
    rng = np.random.default_rng(1)
    for _ in range(30):
        s, t = map(int, rng.choice(net.N, 2, replace=False))
        ref = nx.shortest_path_length(G, s, t, weight="w")
        assert td_dijkstra(net, clock, s, t, 480.0)["eta_min"] == pytest.approx(ref)
        assert td_astar(net, clock, s, t, 480.0)["eta_min"] == pytest.approx(ref)


# Acceptance (Phase 3) ---------------------------------------------------------------------------
def test_synth_builds_fast():
    t = time.time()
    api.build_instance(dict(SYNTH, seed=11, n_customers=60, K=None))
    assert time.time() - t < 5.0


@has_hyd
def test_hyd_loads_from_cache_fast(hyd):
    api._hyd_net.cache_clear()
    t = time.time()
    inst = api.build_instance(HYD)
    assert time.time() - t < 5.0
    assert inst.n == 60 and inst.T_slots.shape == (7, 61, 61)
    geom = api.path_geometry(inst, 4, 0, 1)
    assert len(geom) >= 2 and 17.0 < geom[0][0] < 18.0 and 78.0 < geom[0][1] < 79.0


def test_incident_rebuilds_affected_slots(synth):
    inst, b = synth
    c = inst.coords[1]
    inc = {"type": "zone", "center": [float(c[0]), float(c[1])], "radius_m": 1500, "factor": 2.5,
           "start_min": 1000, "end_min": 1100}
    inst2 = api.build_instance(dict(SYNTH, incidents=[inc]))
    b2 = bundle_for(inst2)
    s = list(b.slot_centers).index(1050.0)
    assert (b2.T_slots[s] >= b.T_slots[s] - 1e-9).all() and (b2.T_slots[s] > b.T_slots[s] + 1e-9).any()
    others = [k for k in range(len(b.slot_centers)) if k != s]
    assert np.allclose(b2.T_slots[others], b.T_slots[others])


def test_infeasible_rejected():
    with pytest.raises(api.InfeasibleScenario):
        api.build_instance(dict(SYNTH, K=1, Q=100))
