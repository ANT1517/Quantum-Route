"""Translate a POST /jobs body into the engine's job dict (§5.3).

Frontend parameter names (§8.1 S3) -> engine names:
  N -> N (GA: pop); alpha_start/alpha_end -> alpha_max/alpha_min with a linear schedule (QPSO);
  iterations -> evaluation budget N * iterations when no budget is given.
No budget at all -> 10 s. A time budget is capped at the job timeout (the OR-Tools stand-in cannot be
interrupted, so its limit must already respect the timeout).
"""
from ..errors import ApiError
from ..settings import JOB_TIMEOUT_S

DEFAULT_TIME_S = 10.0


def engine_job(body, warm_perm: list[int] | None) -> dict:
    if body.algorithm == "milp":
        raise ApiError(422, "UNSUPPORTED", "MILP is the exact baseline for small CVRPLIB P instances only "
                                           "(scripts/run_milp.py); it is not available as a platform job")
    p = body.params.model_dump(exclude_none=True)
    iterations = p.pop("iterations", None)
    a0, a1 = p.pop("alpha_start", None), p.pop("alpha_end", None)
    N = p.get("N")
    if body.algorithm == "qpso" and (a0 is not None or a1 is not None):
        p.update(alpha_mode="linear", alpha_max=a0 if a0 is not None else 1.0, alpha_min=a1 if a1 is not None else 0.5)
    if body.algorithm == "ga" and N is not None:
        p["pop"] = p.pop("N")
    if body.algorithm in ("sa", "ortools"):
        p.pop("N", None)
    budget = body.budget.model_dump()
    if budget["evals"] is None and budget["time_s"] is None:
        if iterations is not None:
            budget["evals"] = int((N or 40) * iterations)
        else:
            budget["time_s"] = DEFAULT_TIME_S
    if budget["time_s"] is not None:
        budget["time_s"] = min(float(budget["time_s"]), JOB_TIMEOUT_S)
    if body.algorithm == "ortools" and budget["time_s"] is None:
        budget["time_s"] = DEFAULT_TIME_S              # OR-Tools runs on a time limit only (§7.8)
    w = body.weights.model_dump(exclude_none=True)
    return {"algorithm": body.algorithm, "weights": w, "params": p, "seed": body.seed, "budget": budget,
            "fleet_mode": body.fleet_mode, "warm_start": {"perm": warm_perm} if warm_perm else None}
