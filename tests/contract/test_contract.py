"""Contract test (Phase 0): catches drift in the frozen §5 contracts on either branch."""
import dataclasses
import json
import re
from pathlib import Path

from qflux.config import load_config
from qflux.types import Instance, Refs, RunRecord, Solution, Weights

from .schema import KPI_KEYS, RESULT_KEYS, ROUTE_KEYS, validate_result

ROOT = Path(__file__).resolve().parents[2]


def _fields(cls):
    return [f.name for f in dataclasses.fields(cls)]


def test_types_frozen():
    assert _fields(Instance) == ["name", "source", "n", "Q", "K", "demand", "service", "coords", "node_ids",
                                 "bks", "distance_convention", "D", "slot_centers", "T_slots", "T0",
                                 "D_slots", "E_slots", "tau0"]
    assert _fields(Weights) == ["wT", "wD", "wC", "wE", "lam"]
    assert _fields(Refs) == ["T", "D", "C", "E"]
    assert _fields(Solution) == ["perm", "routes", "F", "T", "D", "C", "E", "n_vehicles", "feasible", "meta"]
    assert _fields(RunRecord) == ["algo", "instance", "seed", "budget_type", "budget", "best_F", "best_T",
                                  "best_D", "best_C", "best_E", "n_vehicles", "gap_pct", "evals_used",
                                  "wall_s", "curve", "config_hash"]
    assert Weights().lam == 0.5 and Instance.__dataclass_fields__["tau0"].default == 480.0


def test_optimizer_protocol():
    import inspect
    from qflux.algos.base import Optimizer
    params = list(inspect.signature(Optimizer.run).parameters)
    assert params == ["self", "ev", "budget_evals", "budget_s", "rng", "callback", "should_stop", "init_keys"]


def test_config_keys():
    cfg = load_config()
    for k in ["seed_base", "qpso", "pso", "ga", "sa", "ortools", "milp", "budget", "weights_presets",
              "fleet_penalty_lambda", "traffic", "hyd", "synth", "limits"]:
        assert k in cfg, k
    assert cfg["traffic"] == {"bpr_a": 0.15, "bpr_b": 4.0, "platform_scale_S": 25, "fleet_eq_iters": 3}
    for name, w in cfg["weights_presets"].items():
        assert abs(sum(w) - 1.0) < 1e-9, name
    assert cfg["hyd"]["tau0"] == 1050 and cfg["hyd"]["Q"] == 200   # D24


def test_result_ts_matches_python_schema():
    ts = (ROOT / "frontend/src/types/result.ts").read_text(encoding="utf-8")
    body = ts.split("export interface ResultJSON")[1].split("\n}\n")[0]
    for k in RESULT_KEYS | {"edge_flows"}:
        assert re.search(rf"\b{k}\??:", body), f"result.ts missing {k}"
    for k in KPI_KEYS | ROUTE_KEYS:
        assert re.search(rf"\b{k}:", body), f"result.ts missing {k}"


def test_demo_json_matches_contract():
    demo = json.loads((ROOT / "frontend/public/demo/result_demo.json").read_text(encoding="utf-8"))
    validate_result(demo)


def test_api_signatures():
    import inspect
    from qflux import api
    assert list(inspect.signature(api.build_instance).parameters) == ["spec"]
    assert list(inspect.signature(api.run_job).parameters) == ["spec", "job", "progress", "should_stop"]
    for fn in (api.shortest_path, api.fleet_compare):
        assert list(inspect.signature(fn).parameters) == ["spec", "req"]
    assert list(inspect.signature(api.solve_route_qubo).parameters) == ["req"]
