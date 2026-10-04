"""/scenarios (§5.4)."""
from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Incident, Scenario
from ..schemas import EdgesIncident, ScenarioCreate, ZoneIncident
from ..services import scenario_service as svc

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("")
def list_scenarios(db: Session = Depends(get_session)):
    return [svc.summary(s) for s in db.scalars(select(Scenario).order_by(Scenario.created_at)).all()]


@router.post("", status_code=201)
async def create_scenario(body: ScenarioCreate, db: Session = Depends(get_session)):
    data = body.model_dump()
    spec = svc.base_spec(data)
    await run_in_threadpool(svc.validate, spec)      # 422 INFEASIBLE / INVALID_SCENARIO
    s = Scenario(name=body.name, source=body.source, n_customers=body.n_customers, K=body.K, Q=body.Q,
                 seed=body.seed, tau0=body.tau0, spec_json=spec)
    db.add(s)
    db.commit()
    return {"scenario": svc.summary(s)}


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str, db: Session = Depends(get_session)):
    s = svc.get_or_404(db, scenario_id)
    return await run_in_threadpool(svc.detail, db, s)


@router.post("/{scenario_id}/incidents", status_code=201)
async def add_incident(scenario_id: str, body: ZoneIncident | EdgesIncident, db: Session = Depends(get_session)):
    s = svc.get_or_404(db, scenario_id)
    inc = body.model_dump()
    if inc["type"] == "zone":
        inc["center"] = list(inc["center"])
    n = await run_in_threadpool(svc.affected_edges, db, s, inc)
    row = Incident(scenario_id=s.id, spec_json=inc)
    db.add(row)
    db.commit()
    return {"incident_id": row.id, "affected_edges": n}
