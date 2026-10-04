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
def list_benchmarks():
    return results.list_benchmarks()


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
    """Route stops are customer ids of the seeded Hyderabad-60 scenario; the distance matrix is its
    dispatch-slot travel time (minutes). Returns the QUBO matrix and the brute-force optimum for comparison."""
    from qflux.quantum.backends import MAX_STOPS
    if len(body.route_stops) > MAX_STOPS:
        raise ApiError(422, "TOO_MANY_STOPS", f"at most {MAX_STOPS} stops (QUBO has m^2 variables)")
    if len(set(body.route_stops)) != len(body.route_stops):
        raise ApiError(400, "INVALID_INPUT", "route_stops must be distinct")
    s = db.scalars(select(Scenario).where(Scenario.name == "Hyderabad-60")).first()
    if s is None:
        raise ApiError(404, "NOT_FOUND", "seeded scenario Hyderabad-60 is missing")

    def work():
        from qflux.core.construct import dispatch_matrix
        inst = engine.build_instance(svc.engine_spec(db, s))
        if not all(1 <= c <= inst.n for c in body.route_stops):
            raise ApiError(400, "INVALID_INPUT", f"route_stops must be customer ids 1..{inst.n}")
        dist = np.asarray(dispatch_matrix(inst), float)
        try:
            return engine.solve_route_qubo({"route_stops": body.route_stops, "backend": body.backend,
                                            "dist": dist.tolist()})
        except NotImplementedError as e:
            raise ApiError(501, "NOT_IMPLEMENTED", str(e)) from e
    return await run_in_threadpool(work)
