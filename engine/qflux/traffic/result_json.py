"""Assemble ResultJSON (§5.5) from routes evaluated on a TD bundle."""
import hashlib
import json

from qflux.config import load_config
from qflux.explain.templates import route_sentence, summary_sentences
from qflux.types import Instance, Refs, Weights

from .route_eval import evaluate_routes, routes_json
from .td_matrix import TDBundle


def config_hash() -> str:
    return hashlib.sha1(json.dumps(load_config(), sort_keys=True).encode()).hexdigest()[:10]


def build_result(inst: Instance, bundle: TDBundle, routes: list[list[int]], w: Weights, refs: Refs, *,
                 algorithm: str, seed: int, runtime_s: float, evals: int, convergence: list,
                 status: str = "COMPLETED", job_id: str = "local", scenario_id: str = "",
                 ev: dict | None = None, extra_explanation: list[str] | None = None) -> dict:
    ev = ev or evaluate_routes(inst, bundle, routes, w, refs)
    rj = routes_json(inst, bundle, ev, routes)
    from .route_eval import fitness
    kpis = dict(total_time_min=round(ev["T"], 3), total_distance_km=round(ev["D"], 3),
                congestion_delay_min=round(ev["C"], 3), co2_kg=round(ev["E"], 4),
                vehicles_used=int(ev["n_vehicles"]), fleet_limit=inst.K,
                fitness=round(fitness(ev, ev["n_vehicles"], inst.K, w, refs), 6),
                runtime_s=round(runtime_s, 3), evals=int(evals), feasible=_feasible(inst, routes))
    explanation = summary_sentences(kpis, inst.tau0) + [route_sentence(r) for r in rj]
    if extra_explanation:
        explanation = extra_explanation + explanation
    conv = [dict(iter=int(c["iter"]), evals=int(c["evals"]), best_F=float(c["best_F"])) for c in convergence]
    return dict(job_id=job_id, scenario_id=scenario_id or inst.name, algorithm=algorithm, seed=int(seed),
                status=status, weights=dict(wT=w.wT, wD=w.wD, wC=w.wC, wE=w.wE, lam=w.lam), kpis=kpis,
                routes=rj, explanation=explanation, convergence=conv,
                refs=dict(T=round(refs.T, 3), D=round(refs.D, 3), C=round(refs.C, 3), E=round(refs.E, 4)),
                meta=dict(config_hash=config_hash(), instance=inst.name, tau0=float(inst.tau0)))


def _feasible(inst: Instance, routes: list[list[int]]) -> bool:
    """Independent check: every customer exactly once, every load <= Q."""
    seen = [c for r in routes for c in r]
    if sorted(seen) != list(range(1, inst.n + 1)):
        return False
    return all(inst.demand[r].sum() <= inst.Q + 1e-9 for r in routes if r)
