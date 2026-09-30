"""Fleet / dynamic / shortest-path tests T32–T35 (§10.1) on SynthCity (fast, deterministic)."""
import numpy as np
import pytest

from qflux import api
from qflux.api import weights_from
from qflux.dynamic.reroute import held_karp_path, reroute, two_opt_path
from qflux.sp.astar import td_astar
from qflux.sp.td_dijkstra import EdgeClock, td_dijkstra
from qflux.traffic import events
from qflux.traffic.fleet_eq import run_fleet
from qflux.traffic.route_eval import compute_refs
from qflux.traffic.td_matrix import bundle_for

from ..contract.schema import validate_result

SPEC = {"source": "synth", "n_customers": 40, "K": 8, "Q": 150, "tau0": 1050}
W = {"wT": 0.5, "wD": 0.2, "wC": 0.2, "wE": 0.1}


@pytest.fixture(scope="module")
def inst():
    return api.build_instance(SPEC)


@pytest.fixture(scope="module")
def fleet(inst):
    return run_fleet(inst, weights_from(W), S=25, iters=3, time_s=1.5)


# T32 --------------------------------------------------------------------------------------------
def test_t32_msa_steps_decrease(fleet):
    for mode in ("user_eq", "system_opt"):
        steps = [h["step_norm"] for h in fleet[mode]["history"]]
        assert len(steps) == 3
        assert all(b < a for a, b in zip(steps, steps[1:])), (mode, steps)


# T33 --------------------------------------------------------------------------------------------
def test_t33_system_opt_externality_not_worse(fleet):
    naive, so = fleet["naive"]["real"], fleet["system_opt"]["real"]
    print(f"T33 externality naive {naive['externality_veh_h']:.1f} vs system_opt {so['externality_veh_h']:.1f} veh-h")
    assert so["externality_veh_h"] <= naive["externality_veh_h"]


def test_fleet_compare_contract():
    out = api.fleet_compare(SPEC, {"weights": W, "modes": ["naive", "system_opt"], "S": 25, "time_s": 1.0})
    assert set(out["modes"]) == {"naive", "system_opt"}
    for r in out["modes"].values():
        validate_result(r, fleet=True)
        assert r["edge_flows"] and r["kpis"]["feasible"]


# T34 --------------------------------------------------------------------------------------------
def test_t34_incident_reroute(inst):
    from qflux.dynamic.solver import solve
    w = weights_from({"wT": 1.0})
    old = bundle_for(inst)
    refs = compute_refs(inst, old)
    routes = solve(inst, w, refs, budget={"time_s": 1.5})["routes"]
    c = old.net.node_xy[old.terminals[5]]
    inc = {"type": "zone", "center": [float(c[0]), float(c[1])], "radius_m": 2000, "factor": 2.5,
           "start_min": 1040, "end_min": 1160}
    new = bundle_for(api.build_instance(dict(SPEC, incidents=[inc])))
    rr = reroute(inst, old, new, routes, 1065.0, w, refs)
    rep = rr["report"]
    assert rep["delay_increase_min"] > 0                       # the incident hurts
    assert rep["F_final"] <= rep["F_no_reroute"] + 1e-12        # re-optimised never worse than not re-routing
    served = sorted(c for r in rr["routes"] for c in r)
    assert served == list(range(1, inst.n + 1))


def test_incident_api_contract(inst):
    b = bundle_for(inst)
    c = b.net.node_xy[b.terminals[12]]
    inc = {"type": "zone", "center": [float(c[0]), float(c[1])], "radius_m": 2000, "factor": 2.5,
           "start_min": 1040, "end_min": 1160}
    out = api.incident_reroute(SPEC, {"incident": inc, "t_inc": 1065, "weights": {"wT": 1}, "time_s": 1.0})
    validate_result(out["before"]); validate_result(out["after"])
    assert {"accepted", "delay_avoided_min", "reopt_time_s", "eta_change"} <= out["report"].keys()


def test_resequencing_exact():
    rng = np.random.default_rng(0)
    C = rng.uniform(1, 10, (9, 9))
    stops = list(range(2, 9))
    hk = held_karp_path(1, stops, C)

    def cost(seq):
        s = [1] + list(seq) + [0]
        return sum(C[a, b] for a, b in zip(s[:-1], s[1:]))
    import itertools
    best = min(cost(p) for p in itertools.permutations(stops))
    assert cost(hk) == pytest.approx(best)
    assert cost(two_opt_path(1, stops, C)) >= best - 1e-9


# T35 --------------------------------------------------------------------------------------------
def test_t35_astar_equals_dijkstra(inst):
    net = bundle_for(inst).net
    c = net.node_xy[net.N // 2]
    clock = EdgeClock(net, [events.ZoneIncident((float(c[0]), float(c[1])), 1500, 1000, 1100, 2.5)])
    rng = np.random.default_rng(2)
    for _ in range(25):
        s, t = map(int, rng.choice(net.N, 2, replace=False))
        for t0 in (180.0, 1050.0):
            d, a = td_dijkstra(net, clock, s, t, t0), td_astar(net, clock, s, t, t0)
            assert a["eta_min"] == pytest.approx(d["eta_min"])
            assert a["settled"] <= d["settled"]


def test_shortest_path_api():
    out = api.shortest_path(SPEC, {"source": 0, "target": 399, "depart_min": 1050, "algorithm": "astar"})
    assert {"path_geometry", "eta_min", "cost", "runtime_s"} <= out.keys() and len(out["path_geometry"]) > 2
