"""Job manager (§9 Phase 4 step 4): process pool (2 workers), progress via a Manager queue -> asyncio ->
WebSocket subscribers + DB convergence rows, cancel via a shared Event, timeout -> COMPLETED_PARTIAL,
exceptions -> FAILED with the message. Only one manager per backend process."""
import asyncio
import multiprocessing as mp
import queue as queue_mod
import threading
from concurrent.futures import CancelledError, ProcessPoolExecutor
from datetime import datetime, timezone

from ..db import SessionLocal
from ..models import Convergence, Job, Result
from ..settings import JOB_TIMEOUT_S, JOB_WORKERS, MAX_CONCURRENT_JOBS
from . import job_worker

TERMINAL = {"COMPLETED", "COMPLETED_PARTIAL", "FAILED", "CANCELLED"}


def _now():
    return datetime.now(timezone.utc)


class JobManager:
    def __init__(self, workers: int = JOB_WORKERS, timeout_s: float = JOB_TIMEOUT_S):
        self.timeout_s = timeout_s
        ctx = mp.get_context("spawn")
        self._mp = ctx.Manager()
        self.events = self._mp.Queue()
        self.pool = ProcessPoolExecutor(max_workers=workers, mp_context=ctx, initializer=job_worker.init_worker)
        self.active: dict[str, dict] = {}             # job_id -> {future, cancel, budget}
        self.subscribers: dict[str, set[asyncio.Queue]] = {}
        self.loop: asyncio.AbstractEventLoop | None = None
        self._stop = threading.Event()
        self._pump: threading.Thread | None = None

    # ---- lifecycle -----------------------------------------------------------------------------
    def start(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        with SessionLocal() as db:                    # jobs interrupted by a restart cannot resume
            for j in db.query(Job).filter(Job.status.in_(["QUEUED", "RUNNING"])).all():
                j.status, j.error_message, j.finished_at = "FAILED", "backend restarted while the job was running", _now()
            db.commit()
        self._pump = threading.Thread(target=self._pump_events, name="job-events", daemon=True)
        self._pump.start()

    def shutdown(self):
        self._stop.set()
        for a in self.active.values():
            a["cancel"].set()
        self.pool.shutdown(wait=False, cancel_futures=True)
        try:
            self._mp.shutdown()
        except Exception:  # noqa: BLE001
            pass

    # ---- submit / cancel -------------------------------------------------------------------------
    def running_count(self) -> int:
        return len(self.active)

    def can_accept(self) -> bool:
        return self.running_count() < MAX_CONCURRENT_JOBS

    def submit(self, job_id: str, spec: dict, job: dict):
        cancel = self._mp.Event()
        fut = self.pool.submit(job_worker.run, job_id, spec, job, self.events, cancel, self.timeout_s)
        self.active[job_id] = {"future": fut, "cancel": cancel, "budget": job.get("budget") or {}}
        fut.add_done_callback(lambda f, jid=job_id: self.loop.call_soon_threadsafe(self._finish, jid, f))

    def cancel(self, job_id: str) -> bool:
        a = self.active.get(job_id)
        if a is None:
            return False
        a["cancel"].set()
        a["future"].cancel()                          # succeeds only if the job has not started yet
        return True

    # ---- events --------------------------------------------------------------------------------
    def _pump_events(self):
        while not self._stop.is_set():
            try:
                ev = self.events.get(timeout=0.5)
            except queue_mod.Empty:
                continue
            except (EOFError, OSError, BrokenPipeError):
                return
            self.loop.call_soon_threadsafe(self._on_event, ev)

    def _progress_fraction(self, job_id: str, ev: dict) -> float | None:
        b = (self.active.get(job_id) or {}).get("budget") or {}
        fr = []
        if b.get("evals"):
            fr.append(ev.get("evals", 0) / b["evals"])
        if b.get("time_s"):
            fr.append(ev.get("elapsed_s", 0) / b["time_s"])
        return min(1.0, max(fr)) if fr else None

    def _on_event(self, ev: dict):
        jid = ev["job_id"]
        with SessionLocal() as db:
            j = db.get(Job, jid)
            if j is None or j.status in TERMINAL:
                return
            if ev["type"] == "running":
                j.status, j.started_at, j.progress = "RUNNING", _now(), 0.0
            elif ev["type"] == "progress":
                j.status = "RUNNING"
                j.progress = self._progress_fraction(jid, ev)
                db.add(Convergence(job_id=jid, iter=ev["iter"], evals=ev["evals"], best_F=ev["best_F"]))
            db.commit()
        if ev["type"] == "progress":
            self._broadcast(jid, {"type": "progress", "iter": ev["iter"], "evals": ev["evals"], "best_F": ev["best_F"],
                                  "progress": self._progress_fraction(jid, ev)})

    def _finish(self, job_id: str, fut):
        self.active.pop(job_id, None)
        try:
            out = fut.result()
        except CancelledError:
            out = {"status": "CANCELLED", "result": None, "error": None}
        except Exception as e:  # noqa: BLE001  (worker crashed / pool broken)
            out = {"status": "FAILED", "result": None, "error": f"{type(e).__name__}: {e}"}
        with SessionLocal() as db:
            j = db.get(Job, job_id)
            if j is None:
                return
            j.status, j.finished_at = out["status"], _now()
            j.error_message = out.get("error")
            if out.get("result") is not None:
                j.progress = 1.0 if out["status"] == "COMPLETED" else j.progress
                db.merge(Result(job_id=job_id, result_json=out["result"]))
            db.commit()
        if out["status"] == "FAILED":
            self._broadcast(job_id, {"type": "failed", "status": "FAILED", "message": out.get("error")})
        else:
            self._broadcast(job_id, {"type": "completed", "status": out["status"]})
        for qq in self.subscribers.pop(job_id, set()):
            qq.put_nowait(None)                        # tells the socket to close

    # ---- websocket subscribers -------------------------------------------------------------------
    def subscribe(self, job_id: str) -> asyncio.Queue:
        qq: asyncio.Queue = asyncio.Queue()
        self.subscribers.setdefault(job_id, set()).add(qq)
        return qq

    def unsubscribe(self, job_id: str, qq: asyncio.Queue):
        self.subscribers.get(job_id, set()).discard(qq)

    def _broadcast(self, job_id: str, msg: dict):
        for qq in list(self.subscribers.get(job_id, set())):
            qq.put_nowait(msg)
