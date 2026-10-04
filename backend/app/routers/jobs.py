"""/jobs and the WebSocket /ws/jobs/{id} (§5.4)."""
import asyncio

from fastapi import APIRouter, Depends, Header, Request, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal, get_session
from ..errors import ApiError
from ..models import Convergence, Job, Result
from ..schemas import JobCreate
from ..services import scenario_service as svc
from ..services.job_manager import TERMINAL
from ..services.job_params import engine_job

router = APIRouter(prefix="/jobs", tags=["jobs"])
ws_router = APIRouter(tags=["jobs"])


def _job_or_404(db: Session, job_id: str) -> Job:
    j = db.get(Job, job_id)
    if j is None:
        raise ApiError(404, "NOT_FOUND", f"job {job_id} not found")
    return j


@router.post("", status_code=201)
def create_job(body: JobCreate, request: Request, db: Session = Depends(get_session),
               idempotency_key: str | None = Header(default=None)):
    if idempotency_key:                               # double-click Start (§10.2)
        prev = db.scalars(select(Job).where(Job.idempotency_key == idempotency_key)).first()
        if prev is not None:
            return {"job_id": prev.id, "status": prev.status}
    if abs(body.weights.total() - 1.0) > 1e-6:
        raise ApiError(422, "WEIGHTS", f"weights must sum to 1 (got {body.weights.total():.6g})")
    s = svc.get_or_404(db, body.scenario_id)
    manager = request.app.state.jobs
    if not manager.can_accept():
        raise ApiError(429, "TOO_MANY_JOBS", f"{manager.running_count()} jobs are running; try again shortly")
    warm = None
    if body.warm_start_job_id:
        r = db.get(Result, body.warm_start_job_id)
        if r is None:
            raise ApiError(404, "NOT_FOUND", f"warm-start job {body.warm_start_job_id} has no result")
        warm = [int(c) for route in r.result_json.get("routes", []) for c in route["stops"]]
    job = engine_job(body, warm)
    j = Job(scenario_id=s.id, algorithm=body.algorithm, params_json={**job["params"], "budget": job["budget"]},
            weights_json=job["weights"], seed=body.seed, fleet_mode=body.fleet_mode, status="QUEUED",
            idempotency_key=idempotency_key)
    db.add(j)
    db.commit()
    manager.submit(j.id, svc.engine_spec(db, s), job)
    return {"job_id": j.id, "status": "QUEUED"}


@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_session)):
    j = _job_or_404(db, job_id)
    return {"status": j.status, "progress": j.progress, "error_message": j.error_message}


@router.get("/{job_id}/result")
def get_result(job_id: str, db: Session = Depends(get_session)):
    j = _job_or_404(db, job_id)
    r = db.get(Result, job_id)
    if r is None:
        if j.status in TERMINAL:
            raise ApiError(404, "NO_RESULT", f"job {job_id} ended with status {j.status} and no result")
        raise ApiError(409, "NOT_FINISHED", f"job {job_id} is {j.status}")
    return r.result_json


@router.get("/{job_id}/convergence")
def get_convergence(job_id: str, db: Session = Depends(get_session)):
    _job_or_404(db, job_id)
    r = db.get(Result, job_id)
    if r is not None and r.result_json.get("convergence"):
        return r.result_json["convergence"]
    rows = db.scalars(select(Convergence).where(Convergence.job_id == job_id).order_by(Convergence.iter)).all()
    return [{"iter": c.iter, "evals": c.evals, "best_F": c.best_F} for c in rows]


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, request: Request):
    with SessionLocal() as db:
        j = _job_or_404(db, job_id)
        if j.status in TERMINAL:
            raise ApiError(409, "ALREADY_FINISHED", f"job {job_id} is {j.status}")
    request.app.state.jobs.cancel(job_id)
    for _ in range(100):                              # wait up to ~10 s for the worker to hand back best-so-far
        await asyncio.sleep(0.1)
        with SessionLocal() as db:
            st = db.get(Job, job_id).status
        if st in TERMINAL:
            return {"status": st}
    return {"status": "CANCELLING"}


@ws_router.websocket("/ws/jobs/{job_id}")
async def job_socket(ws: WebSocket, job_id: str):
    await ws.accept()
    with SessionLocal() as db:
        j = db.get(Job, job_id)
        status = None if j is None else j.status
    if status is None:
        await ws.close(code=4404)
        return
    manager = ws.app.state.jobs
    if status in TERMINAL:
        await ws.send_json({"type": "failed" if status == "FAILED" else "completed", "status": status})
        await ws.close()
        return
    q = manager.subscribe(job_id)
    try:
        while True:
            msg = await q.get()
            if msg is None:
                break
            await ws.send_json(msg)
        await ws.close()
    except WebSocketDisconnect:
        pass
    finally:
        manager.unsubscribe(job_id, q)
