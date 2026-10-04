"""QuantumRoute backend (§4.1, §9 Phase 4): FastAPI + SQLite + process-pool job manager.

    uvicorn backend.app.main:app --port 8000          (from the repo root)
OpenAPI docs at /docs. REST under /api, WebSocket at /ws/jobs/{id} (the frontend expects it at the root).
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import errors
from .db import Base, SessionLocal, engine
from .models import Scenario
from .routers import jobs, misc, scenarios
from .services.job_manager import JobManager
from .services.scenario_service import base_spec
from .settings import CORS_ORIGINS, SEED_SCENARIOS, VERSION


def seed_scenarios():
    with SessionLocal() as db:
        for sc in SEED_SCENARIOS:
            if db.query(Scenario).filter(Scenario.name == sc["name"]).first() is None:
                db.add(Scenario(**sc, spec_json=base_spec(sc)))
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    seed_scenarios()
    app.state.jobs = JobManager()
    app.state.jobs.start(asyncio.get_running_loop())
    try:
        yield
    finally:
        app.state.jobs.shutdown()


app = FastAPI(title="QuantumRoute API", version=VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=False, allow_methods=["*"],
                   allow_headers=["*"])
errors.install(app)
app.include_router(misc.router, prefix="/api")
app.include_router(scenarios.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(jobs.ws_router)
