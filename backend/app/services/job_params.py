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
    # result labels -> engine settings (integration fix: re-optimize sends the previous result's label)
    alias = {"qpso_noqubo_tuned": {}, "qpso_noqubo": {"alpha_mode": "adaptive"}, "qpso_full": {"qubo_slot": True},
             "qpso_tuned_qubo": {"qubo_slot": True}, "qpso_linear_qubo": {"qubo_slot": True},
             "qpso_noqubo_linear": {}}            # re-optimize of a custom-alpha run falls back to the tuned alpha
    if body.algorithm in alias:
        extra = alias[body.algorithm]
        body = body.model_copy(update={"algorithm": "qpso"})
        if extra.get("qubo_slot"):
            p["qubo_slot"] = True
        if "alpha_mode" in extra:
            p["alpha_mode"] = extra["alpha_mode"]
    iterations = p.pop("iterations", None)
    a0, a1 = p.pop("alpha_start", None), p.pop("alpha_end", None)
    N = p.get("N")
    qubo = bool(p.pop("qubo_slot", False) or False)
    if body.algorithm == "qpso":
        # D59: default engine = QPSO-noQUBO (tuned): QUBO slot off, fixed alpha 0.3 (D54). qubo_slot=true (D60) keeps
        # the tuned alpha and only switches the QUBO slot on; alpha_start/alpha_end override alpha (linear schedule).
        p["qubo_slot"] = {"enabled": qubo}
        if a0 is None and a1 is None and p.get("alpha_mode") != "adaptive":
            from qflux.algos.registry import TUNED_NOQUBO
            p.update(alpha_mode=TUNED_NOQUBO["alpha_mode"], alpha_fixed=TUNED_NOQUBO["alpha_fixed"])
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
    if body.algorithm == "ortools" and budget["time_s"] is None:
        budget["time_s"] = DEFAULT_TIME_S              # OR-Tools runs on a time limit only (§7.8)
    # The job timeout must reach the optimizer's own deadline (D31: LS, QUBO slot and polish stop at it);
    # should_stop alone is only checked between iterations, so one long LS pass could overrun it.
    timeout_bound = budget["time_s"] is None or float(budget["time_s"]) > JOB_TIMEOUT_S
    budget["time_s"] = min(float(budget["time_s"]), JOB_TIMEOUT_S) if budget["time_s"] is not None else JOB_TIMEOUT_S
    w = body.weights.model_dump(exclude_none=True)
    return {"algorithm": body.algorithm, "weights": w, "params": p, "seed": body.seed, "budget": budget,
            "timeout_bound": timeout_bound,
            "label": (_qpso_label(qubo, a0 is not None or a1 is not None, p.get("alpha_mode") == "adaptive")
                      if body.algorithm == "qpso" else body.algorithm),
            "fleet_mode": body.fleet_mode, "warm_start": {"perm": warm_perm} if warm_perm else None}


def _qpso_label(qubo: bool, custom_alpha: bool, adaptive: bool) -> str:
    """Result labels (D59/D60): one name per configuration, so labels are never mixed."""
    if qubo:
        return "qpso_linear_qubo" if custom_alpha else "qpso_full" if adaptive else "qpso_tuned_qubo"
    return "qpso_noqubo_linear" if custom_alpha else "qpso_noqubo" if adaptive else "qpso_noqubo_tuned"
