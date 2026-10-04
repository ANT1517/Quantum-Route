"""Engine entry points used by the backend (§5.3). All return plain JSON-serialisable dicts."""
import json
import time
from functools import lru_cache
from pathlib import Path

import numpy as np

from qflux.config import REPO_ROOT, load_config
from qflux.types import Instance, Weights

DEMO_DIR = REPO_ROOT / "frontend" / "public" / "demo"
HYD_CACHE = REPO_ROOT / "data" / "hyd" / "cache"
SYNTH_CACHE = REPO_ROOT / "data" / "synth"


class InfeasibleScenario(ValueError):
    """Maps to HTTP 422 INFEASIBLE (§5.4)."""


# ---------------------------------------------------------------------------------------------
# Instances
# ---------------------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _hyd_net():
    from qflux.traffic.hyd_graph import load_roadnet
    return load_roadnet()


@lru_cache(maxsize=8)
def _synth_net(grid: int, seed: int):
    from qflux.traffic.synth_city import build_synth
    return build_synth(grid=grid, seed=seed)


def road_net(spec: dict):
    src = spec.get("source", "hyderabad")
    if src == "hyderabad":
        return _hyd_net()
    if src == "synth":
        return _synth_net(int(spec.get("grid", load_config()["synth"]["grid"])), int(spec.get("seed", 0)))
    raise ValueError(f"source {src!r} has no road network")


def _validate(n: int, demand: np.ndarray, Q: float, K: int | None) -> None:
    if n > load_config()["limits"]["max_customers"]:
        raise InfeasibleScenario(f"n_customers {n} above limit")
    if demand.max() > Q:
        raise InfeasibleScenario(f"a single demand ({demand.max():.0f}) exceeds capacity Q={Q:.0f}")
    if K is not None and demand.sum() > K * Q:
        raise InfeasibleScenario(f"total demand {demand.sum():.0f} exceeds K*Q = {K * Q:.0f}")


def build_instance(spec: dict) -> Instance:
    """spec: {"source": "hyderabad"|"synth"|"cvrplib", "name", "n_customers", "K", "Q", "seed", "tau0",
    "incidents": [...]}"""
    from qflux.traffic import events, td_matrix
    src = spec.get("source", "hyderabad")
    if src == "cvrplib":
        from qflux.bench.loader import load_instance   # Person A's module
        return load_instance(spec["name"])
    cfg = load_config()
    hyd = cfg["hyd"]
    n = int(spec.get("n_customers", hyd["n_customers"]))
    seed = int(spec.get("seed", 7 if src == "hyderabad" else 0))
    K = spec.get("K", hyd["K"])
    K = None if K is None else int(K)
    Q = float(spec.get("Q", hyd["Q"]))
    tau0 = float(spec.get("tau0", hyd["tau0"]))
    incidents = [events.from_spec(d) if isinstance(d, dict) else d for d in spec.get("incidents", [])]
    net = road_net(spec)

    if src == "hyderabad":
        from qflux.traffic.hyd_graph import load_customers
        df = load_customers(net, n, seed)
        terminals = df["node_index"].to_numpy(np.int64)
        demand = df["demand"].to_numpy(float)
        service = df["service"].to_numpy(float)
        cache = HYD_CACHE
        key = dict(src=src, n=n, seed=seed)
    elif src == "synth":
        from qflux.traffic.synth_city import synth_customers
        terminals, demand, service = synth_customers(net, n, seed)
        cache = SYNTH_CACHE
        key = dict(src=src, n=n, seed=seed, grid=int(round(np.sqrt(net.N))))
    else:
        raise ValueError(f"unknown source {src!r}")
    _validate(n, demand, Q, K)

    bundle = td_matrix.get_bundle(net, terminals, incidents, cache, key)
    name = f"{src}-{n}" + (f"-s{seed}" if seed != (7 if src == "hyderabad" else 0) else "")
    if incidents:
        name += "-inc" + td_matrix.cache_key({"i": [events.to_spec(i) for i in incidents]})[:6]
    from qflux.traffic.profiles import nearest_slot
    s0 = nearest_slot(tau0, bundle.slot_centers)
    inst = Instance(name=spec.get("name") or name, source=src, n=n, Q=Q, K=K, demand=demand, service=service,
                    coords=net.node_xy[terminals].copy(), node_ids=[int(net.node_id[t]) for t in terminals],
                    distance_convention="road", D=bundle.D_slots[s0].copy(),
                    slot_centers=bundle.slot_centers.copy(), T_slots=bundle.T_slots, T0=bundle.T0,
                    D_slots=bundle.D_slots, E_slots=bundle.E_slots, tau0=tau0)
    td_matrix.register(inst.name, bundle)
    return inst


def path_geometry(inst: Instance, slot: int, i: int, j: int) -> list[list[float]]:
    from qflux.traffic.td_matrix import bundle_for
    return bundle_for(inst).path_geometry(slot, i, j)


def scenario_detail(spec: dict) -> dict:
    """{scenario, customers[{id,lat,lon,demand}], depot} for GET /scenarios/{id} (§5.4)."""
    inst = build_instance(spec)
    c = inst.coords
    return {"scenario": dict(spec, name=inst.name),
            "customers": [{"id": i, "lat": float(c[i, 0]), "lon": float(c[i, 1]), "demand": float(inst.demand[i])}
                          for i in range(1, inst.n + 1)],
            "depot": {"lat": float(c[0, 0]), "lon": float(c[0, 1])}}


# ---------------------------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------------------------
def weights_from(d: dict | None) -> Weights:
    d = d or {}
    return Weights(wT=float(d.get("wT", 1.0)), wD=float(d.get("wD", 0.0)), wC=float(d.get("wC", 0.0)),
                   wE=float(d.get("wE", 0.0)),
                   lam=float(d.get("lam", load_config()["fleet_penalty_lambda"])))


def run_job(spec: dict, job: dict, progress=None, should_stop=None) -> dict:
    """job: {"algorithm", "weights", "params", "seed", "budget": {"evals", "time_s"}, "fleet_mode",
    "warm_start": {"perm": [...]} | None} -> ResultJSON (§5.5)."""
    if spec.get("source") == "cvrplib":
        return _demo("result_demo.json")
    from qflux.dynamic.solver import solve
    from qflux.traffic.result_json import build_result
    from qflux.traffic.route_eval import compute_refs
    from qflux.traffic.td_matrix import bundle_for

    inst = build_instance(spec)
    bundle = bundle_for(inst)
    w = weights_from(job.get("weights"))
    refs = compute_refs(inst, bundle)
    t = time.time()
    warm = (job.get("warm_start") or {}).get("perm")
    from qflux.algos.registry import DEFAULT_ENGINE
    sol = solve(inst, w, refs, algorithm=job.get("algorithm", DEFAULT_ENGINE), seed=int(job.get("seed", 0)),
                budget=job.get("budget") or {}, params=job.get("params") or {}, warm_start_perm=warm,
                progress=progress, should_stop=should_stop)
    status = "COMPLETED_PARTIAL" if sol.get("partial") else "COMPLETED"
    return build_result(inst, bundle, sol["routes"], w, refs, algorithm=sol["algorithm"],
                        seed=int(job.get("seed", 0)), runtime_s=time.time() - t, evals=sol.get("evals", 0),
                        convergence=sol.get("convergence", []), status=status,
                        job_id=str(job.get("job_id", "local")), scenario_id=str(spec.get("id", inst.name)))


def shortest_path(spec: dict, req: dict) -> dict:
    """req: {source, target, depart_min, algorithm: dijkstra|astar, weights, incidents?}"""
    from qflux.sp.service import shortest_path_request
    return shortest_path_request(road_net(spec), req)


def fleet_compare(spec: dict, req: dict) -> dict:
    """req: {modes, S, weights, seed} -> {modes: {mode: FleetResult}}"""
    from qflux.traffic.fleet_eq import fleet_compare_request
    inst = build_instance(spec)
    return fleet_compare_request(inst, req, scenario_id=str(spec.get("id", inst.name)))


def incident_reroute(spec: dict, req: dict) -> dict:
    """req: {incident: §5.4 incident body, t_inc, weights, routes?, seed, time_s}
    -> {incident, before: ResultJSON, after: ResultJSON, report} (Results screen, J2)."""
    from qflux.dynamic.reroute import reroute
    from qflux.dynamic.solver import solve
    from qflux.traffic.result_json import build_result
    from qflux.traffic.route_eval import compute_refs
    from qflux.traffic.td_matrix import bundle_for

    inst = build_instance(spec)
    old = bundle_for(inst)
    w = weights_from(req.get("weights"))
    refs = compute_refs(inst, old)
    seed = int(req.get("seed", 0))
    routes = req.get("routes")
    t = time.time()
    if routes is None:
        from qflux.algos.registry import DEFAULT_ENGINE
        sol = solve(inst, w, refs, algorithm=req.get("algorithm", DEFAULT_ENGINE), seed=seed,
                    budget={"time_s": float(req.get("time_s", 5.0))})
        routes, algo = sol["routes"], sol["algorithm"]
    else:
        algo = req.get("algorithm", "given")
    plan_s = time.time() - t
    inc = req["incident"]
    inst_new = build_instance(dict(spec, incidents=list(spec.get("incidents", [])) + [inc]))
    new = bundle_for(inst_new)
    t_inc = float(req.get("t_inc", inc["start_min"]))
    rr = reroute(inst, old, new, routes, t_inc, w, refs)
    sid = str(spec.get("id", inst.name))
    before = build_result(inst, old, routes, w, refs, algorithm=algo, seed=seed, runtime_s=plan_s, evals=0,
                          convergence=[], job_id="incident-before", scenario_id=sid)
    after = build_result(inst_new, rr["bundle"], rr["routes"], w, refs, algorithm=f"{algo}+reroute", seed=seed,
                         runtime_s=rr["report"]["reopt_time_s"], evals=0, convergence=[],
                         job_id="incident-after", scenario_id=sid, extra_explanation=rr["report"]["sentences"])
    return {"incident": inc, "before": before, "after": after, "report": rr["report"]}


def solve_route_qubo(req: dict) -> dict:
    try:
        from qflux.quantum.backends import solve_route_request   # Person A's module
    except ImportError:
        raise NotImplementedError("quantum slot lives on the solver branch")
    return solve_route_request(req)


def _demo(name: str) -> dict:
    return json.loads((DEMO_DIR / name).read_text(encoding="utf-8"))
