"""Scenario <-> engine spec (§5.3). The engine builds instances from a spec dict; the DB stores the spec."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from qflux import api as engine

from ..errors import ApiError
from ..models import Incident, Scenario


def summary(s: Scenario) -> dict:
    return {"id": s.id, "name": s.name, "source": s.source, "n_customers": s.n_customers, "K": s.K, "Q": s.Q,
            "seed": s.seed, "tau0": s.tau0}


def base_spec(body: dict) -> dict:
    """Engine spec from a create request. The user's display name is NOT passed for road-network sources:
    the engine keys its matrix cache by instance name, so it must come from the spec itself."""
    spec = {k: body[k] for k in ("source", "n_customers", "K", "Q", "seed", "tau0")}
    if body["source"] == "cvrplib":
        spec["name"] = body["name"]                   # CVRPLIB: the name is the instance (e.g. A-n32-k5)
    return spec


def engine_spec(db: Session, s: Scenario) -> dict:
    incidents = db.scalars(select(Incident).where(Incident.scenario_id == s.id).order_by(Incident.created_at)).all()
    spec = dict(s.spec_json)
    spec["id"] = s.id
    spec["incidents"] = [i.spec_json for i in incidents]
    return spec


def validate(spec: dict) -> None:
    """Build the instance once: rejects demand > K*Q, a single demand > Q, unreachable customers (422)."""
    try:
        engine.build_instance(spec)
    except engine.InfeasibleScenario as e:
        raise ApiError(422, "INFEASIBLE", str(e)) from e
    except (ValueError, FileNotFoundError, KeyError) as e:
        raise ApiError(422, "INVALID_SCENARIO", str(e)) from e


def get_or_404(db: Session, scenario_id: str) -> Scenario:
    s = db.get(Scenario, scenario_id)
    if s is None:
        raise ApiError(404, "NOT_FOUND", f"scenario {scenario_id} not found")
    return s


def detail(db: Session, s: Scenario) -> dict:
    spec = engine_spec(db, s)
    if s.source == "cvrplib":                         # no lat/lon for CVRPLIB: return planar x/y as lat/lon
        inst = engine.build_instance(spec)
        c = inst.coords
        return {"scenario": summary(s),
                "customers": [{"id": i, "lat": float(c[i, 1]), "lon": float(c[i, 0]), "demand": float(inst.demand[i])}
                              for i in range(1, inst.n + 1)],
                "depot": {"lat": float(c[0, 1]), "lon": float(c[0, 0])}, "coordinates": "planar"}
    d = engine.scenario_detail(spec)
    d["scenario"] = summary(s)
    return d


def affected_edges(db: Session, s: Scenario, incident: dict) -> int:
    from qflux.traffic import events
    if s.source == "cvrplib":
        raise ApiError(400, "NO_ROAD_NETWORK", "CVRPLIB scenarios have no road network for incidents")
    net = engine.road_net(engine_spec(db, s))
    return int(len(events.affected_edges(net, events.from_spec(incident))))
