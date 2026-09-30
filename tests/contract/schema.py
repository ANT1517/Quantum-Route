"""Python mirror of the frozen ResultJSON contract (§5.5 / frontend/src/types/result.ts)."""
import numbers

RESULT_KEYS = {"job_id", "scenario_id", "algorithm", "seed", "status", "weights", "kpis", "routes",
               "explanation", "convergence", "refs", "meta"}
OPTIONAL_KEYS = {"edge_flows"}
WEIGHT_KEYS = {"wT", "wD", "wC", "wE", "lam"}
KPI_KEYS = {"total_time_min", "total_distance_km", "congestion_delay_min", "co2_kg", "vehicles_used",
            "fleet_limit", "fitness", "runtime_s", "evals", "feasible"}
ROUTE_KEYS = {"vehicle", "stops", "load", "capacity", "time_min", "distance_km", "congestion_delay_min",
              "co2_kg", "depart_min", "return_min", "geometry", "color"}
EDGE_FLOW_KEYS = {"geometry", "fleet_flow", "vc_ratio"}
CONV_KEYS = {"iter", "evals", "best_F"}
REF_KEYS = {"T", "D", "C", "E"}
META_KEYS = {"config_hash", "instance", "tau0"}
FLEET_EXTRA_KEYS = {"externality_veh_h", "max_vc", "edges_over_capacity", "corridors_used"}


def _num(x):
    return isinstance(x, numbers.Real) and not isinstance(x, bool)


def _keys(obj, required, where, optional=frozenset()):
    missing = required - obj.keys()
    extra = obj.keys() - required - optional
    assert not missing, f"{where}: missing {sorted(missing)}"
    assert not extra, f"{where}: unexpected {sorted(extra)}"


def _geometry(g, where):
    assert isinstance(g, list), where
    for p in g:
        assert isinstance(p, list) and len(p) == 2 and _num(p[0]) and _num(p[1]), f"{where}: bad point {p}"


def validate_result(r: dict, fleet: bool = False) -> None:
    _keys(r, RESULT_KEYS | (FLEET_EXTRA_KEYS if fleet else set()), "result", OPTIONAL_KEYS)
    assert isinstance(r["job_id"], str) and isinstance(r["scenario_id"], str)
    assert isinstance(r["algorithm"], str) and isinstance(r["seed"], int)
    assert r["status"] in ("COMPLETED", "COMPLETED_PARTIAL")
    _keys(r["weights"], WEIGHT_KEYS, "weights")
    _keys(r["kpis"], KPI_KEYS, "kpis")
    for k, v in r["kpis"].items():
        if k == "feasible":
            assert isinstance(v, bool)
        elif k == "fleet_limit":
            assert v is None or isinstance(v, int)
        else:
            assert _num(v), f"kpis.{k}"
    for i, rt in enumerate(r["routes"]):
        _keys(rt, ROUTE_KEYS, f"routes[{i}]")
        assert all(isinstance(s, int) for s in rt["stops"])
        _geometry(rt["geometry"], f"routes[{i}].geometry")
        assert isinstance(rt["color"], str)
    for i, e in enumerate(r.get("edge_flows") or []):
        _keys(e, EDGE_FLOW_KEYS, f"edge_flows[{i}]")
        _geometry(e["geometry"], f"edge_flows[{i}].geometry")
    assert all(isinstance(s, str) for s in r["explanation"])
    for c in r["convergence"]:
        _keys(c, CONV_KEYS, "convergence")
    _keys(r["refs"], REF_KEYS, "refs")
    _keys(r["meta"], META_KEYS, "meta")
    if fleet:
        for k in FLEET_EXTRA_KEYS:
            assert _num(r[k]), k
