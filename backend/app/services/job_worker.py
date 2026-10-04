"""Runs one optimization job in a worker process (§9 Phase 4 step 4).

Progress events go through a multiprocessing.Manager queue; cancellation through a shared Event. The job
timeout is enforced through should_stop, so the optimizer returns its best-so-far (COMPLETED_PARTIAL).
"""
import time
import traceback


def init_worker():
    import os
    os.environ.setdefault("NUMBA_NUM_THREADS", "1")
    from .. import settings  # noqa: F401  (puts engine/ on sys.path)


def run(job_id: str, spec: dict, job: dict, q, cancel, timeout_s: float):
    """-> {"status", "result" | None, "error" | None}."""
    from qflux import api as engine
    t0 = time.time()
    state = {"timeout": False}

    def should_stop():
        if cancel.is_set():
            return True
        if time.time() - t0 > timeout_s:
            state["timeout"] = True
            return True
        return False

    def progress(ev: dict):
        q.put({"job_id": job_id, "type": "progress", "iter": int(ev.get("iter", 0)), "evals": int(ev.get("evals", 0)),
               "best_F": float(ev.get("best_F", float("nan"))), "elapsed_s": float(ev.get("elapsed_s", time.time() - t0))})

    q.put({"job_id": job_id, "type": "running"})
    try:
        res = engine.run_job(spec, dict(job, job_id=job_id), progress=progress, should_stop=should_stop)
    except Exception as e:  # noqa: BLE001  -> FAILED + message (§10.2)
        return {"status": "FAILED", "result": None, "error": f"{type(e).__name__}: {e}",
                "trace": traceback.format_exc(limit=5)}
    # the timeout cap was the binding limit: the run ended at the job timeout before its own budget
    hit_timeout = bool(job.get("timeout_bound")) and time.time() - t0 >= 0.95 * timeout_s
    if cancel.is_set():
        status = "CANCELLED"
    elif state["timeout"] or hit_timeout or res.get("status") == "COMPLETED_PARTIAL":
        status = "COMPLETED_PARTIAL"
    else:
        status = "COMPLETED"
    res["status"] = "COMPLETED_PARTIAL" if status in ("COMPLETED_PARTIAL", "CANCELLED") else "COMPLETED"
    if job.get("label") and res.get("algorithm") == job.get("algorithm"):
        res["algorithm"] = job["label"]                # D53: say which QPSO variant ran (qpso_noqubo / qpso_full)
    return {"status": status, "result": res, "error": None}
