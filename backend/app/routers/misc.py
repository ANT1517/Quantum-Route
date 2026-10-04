"""/health, /shortest-path, /fleet-compare, /benchmarks, /files, /quantum (§5.4)."""
import numpy as np
from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from qflux import api as engine

from ..db import get_session
from ..errors import ApiError
from ..models import Scenario
from ..schemas import FleetCompareIn, ShortestPathIn, SolveRouteIn
from ..services import results_service as results
from ..services import scenario_service as svc
from ..settings import VERSION

router = APIRouter()


@router.get("/health", tags=["health"])
def health():
    return {"status": "ok", "version": VERSION}


@router.post("/shortest-path", tags=["shortest path"])
async def shortest_path(body: ShortestPathIn, db: Session = Depends(get_session)):
    s = svc.get_or_404(db, body.scenario_id)
    if s.source == "cvrplib":
        raise ApiError(400, "NO_ROAD_NETWORK", "shortest path needs a road network (Hyderabad or SynthCity)")
    if body.algorithm == "qpso":
        raise ApiError(501, "NOT_IMPLEMENTED", "QPSO shortest path is P1 (cut list #4); use dijkstra or astar")
    spec = svc.engine_spec(db, s)
    req = body.model_dump(exclude_none=True)
    req["source"], req["target"] = list(body.source), list(body.target)
    req["incidents"] = spec.get("incidents", [])
    from qflux.sp.service import NoPath
    try:
        return await run_in_threadpool(engine.shortest_path, spec, req)
    except NoPath as e:
        raise ApiError(404, "NO_PATH", str(e)) from e


@router.post("/fleet-compare", tags=["fleet"])
async def fleet_compare(body: FleetCompareIn, db: Session = Depends(get_session)):
    if abs(body.weights.total() - 1.0) > 1e-6:
        raise ApiError(422, "WEIGHTS", f"weights must sum to 1 (got {body.weights.total():.6g})")
    s = svc.get_or_404(db, body.scenario_id)
    if s.source == "cvrplib":
        raise ApiError(400, "NO_ROAD_NETWORK", "fleet comparison needs a road network")
    spec = svc.engine_spec(db, s)
    req = {"modes": body.modes, "S": body.S, "weights": body.weights.model_dump(exclude_none=True), "seed": body.seed}
    return await run_in_threadpool(engine.fleet_compare, spec, req)


@router.get("/benchmarks", tags=["benchmarks"])
def list_benchmarks(all: bool = False):  # noqa: A002  (query parameter name)
    """Benchmarks only; ?all=true also lists tuning and smoke tables (each item carries its kind)."""
    return results.list_benchmarks(include_all=all)


@router.get("/benchmarks/{name}", tags=["benchmarks"])
def get_benchmark(name: str):
    return results.benchmark(name)


@router.get("/files/{path:path}", tags=["files"])
def get_file(path: str):
    p, media = results.safe_file(path)
    return FileResponse(p, media_type=media)


@router.get("/quantum/validation", tags=["quantum"])
def quantum_validation():
    return results.qubo_validation()


@router.post("/quantum/solve-route", tags=["quantum"])
async def solve_route(body: SolveRouteIn, db: Session = Depends(get_session)):
    """Route stops are customer ids of a scenario; the distance matrix is that scenario's dispatch-slot
    travel time (minutes). The scenario comes from job_id or scenario_id if given; otherwise from the most
    recent job whose result contains exactly this route (Quantum Lab sends a route of the last job);
    otherwise Hyderabad-60. The response says which scenario was used."""
    from qflux.quantum.backends import MAX_STOPS
    if len(body.route_stops) > MAX_STOPS:
        raise ApiError(422, "TOO_MANY_STOPS", f"at most {MAX_STOPS} stops (QUBO has m^2 variables)")
    if len(set(body.route_stops)) != len(body.route_stops):
        raise ApiError(400, "INVALID_INPUT", "route_stops must be distinct")
    s = _route_scenario(db, body)

    def work():
        from qflux.core.construct import dispatch_matrix
        inst = engine.build_instance(svc.engine_spec(db, s))
        if not all(1 <= c <= inst.n for c in body.route_stops):
            raise ApiError(400, "INVALID_INPUT", f"route_stops must be customer ids 1..{inst.n}")
        dist = np.asarray(dispatch_matrix(inst), float)
        try:
            out = engine.solve_route_qubo({"route_stops": body.route_stops, "backend": body.backend,
                                           "dist": dist.tolist()})
        except NotImplementedError as e:
            raise ApiError(501, "NOT_IMPLEMENTED", str(e)) from e
        out["scenario_id"], out["scenario_name"] = s.id, s.name
        return out
    return await run_in_threadpool(work)


def _route_scenario(db: Session, body: SolveRouteIn) -> Scenario:
    from ..models import Job, Result
    if body.scenario_id:
        return svc.get_or_404(db, body.scenario_id)
    if body.job_id:
        j = db.get(Job, body.job_id)
        if j is None:
            raise ApiError(404, "NOT_FOUND", f"job {body.job_id} not found")
        return svc.get_or_404(db, j.scenario_id)
    rows = db.execute(select(Result, Job).join(Job, Job.id == Result.job_id).order_by(Result.created_at.desc())
                      .limit(200)).all()
    for res, job in rows:
        if any(list(r.get("stops", [])) == list(body.route_stops) for r in res.result_json.get("routes", [])):
            return svc.get_or_404(db, job.scenario_id)
    s = db.scalars(select(Scenario).where(Scenario.name == "Hyderabad-60")).first()
    if s is None:
        raise ApiError(404, "NOT_FOUND", "seeded scenario Hyderabad-60 is missing")
    return s
