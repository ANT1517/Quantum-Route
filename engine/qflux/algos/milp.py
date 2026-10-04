"""Reference MILP for small static CVRP (§3.2): two-index formulation with MTZ load constraints, PuLP/CBC.

MTZ is a weak formulation: within a time limit CBC usually finds good solutions but cannot close the gap.
Results therefore report CBC's own status, best value, bound and gap, read from the CBC log, and claim an
optimum only when CBC proved one ("optimal": gap closed before the limit). Proven optima for the
P instances come from their .sol files, not from this MILP (T11).
"""
import re
import tempfile
import time
from pathlib import Path

from qflux.config import load_config


def _parse_cbc_log(text: str) -> dict:
    def num(pattern):
        m = re.findall(pattern, text)
        return float(m[-1]) if m else None
    result = re.findall(r"Result - (.+)", text)
    return {"cbc_result": result[-1].strip() if result else None,
            "objective": num(r"Objective value:\s+([-\d.eE+]+)"),
            "bound": num(r"Lower bound:\s+([-\d.eE+]+)"),
            "gap_cbc": num(r"Gap:\s+([-\d.eE+]+)")}


def solve_milp(inst, time_limit_s: float | None = None, K: int | None = None, msg: bool = False) -> dict:
    import pulp
    cfg = load_config()["milp"]
    if inst.n > cfg["max_n"]:
        raise ValueError(f"MILP limited to n <= {cfg['max_n']}")
    limit = float(time_limit_s or cfg["time_limit_s"])
    n, Q, C = inst.n, float(inst.Q), inst.D
    V = range(n + 1)
    cust = range(1, n + 1)
    prob = pulp.LpProblem("cvrp", pulp.LpMinimize)
    x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", cat="Binary") for i in V for j in V if i != j}
    u = {i: pulp.LpVariable(f"u_{i}", lowBound=float(inst.demand[i]), upBound=Q) for i in cust}
    prob += pulp.lpSum(C[i, j] * x[i, j] for (i, j) in x)
    for j in cust:
        prob += pulp.lpSum(x[i, j] for i in V if i != j) == 1
        prob += pulp.lpSum(x[j, k] for k in V if k != j) == 1
    prob += pulp.lpSum(x[0, j] for j in cust) == pulp.lpSum(x[i, 0] for i in cust)
    if K is not None:
        prob += pulp.lpSum(x[0, j] for j in cust) <= K
    for i in cust:
        for j in cust:
            if i != j:
                prob += u[i] - u[j] + Q * x[i, j] <= Q - float(inst.demand[j])
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "cbc.log"
        t = time.time()
        status = prob.solve(pulp.PULP_CBC_CMD(msg=msg, timeLimit=limit, logPath=str(log)))
        wall = time.time() - t
        info = _parse_cbc_log(log.read_text(errors="replace") if log.exists() else "")
    succ = {i: j for (i, j), var in x.items() if var.value() is not None and var.value() > 0.5}
    routes = []
    for (i, j), var in x.items():
        if i == 0 and var.value() is not None and var.value() > 0.5:
            r, cur = [], j
            while cur != 0:
                r.append(cur)
                cur = succ[cur]
            routes.append(r)
    best = info["objective"] if info["objective"] is not None else pulp.value(prob.objective)
    bound = info["bound"]
    gap = None
    if best is not None and bound is not None and best > 0:
        gap = 100.0 * (best - bound) / best
    proved = (info["cbc_result"] or "").lower().startswith("optimal solution found")
    return {"status": pulp.LpStatus[status], "cbc_result": info["cbc_result"], "optimal": proved,
            "objective": None if best is None else float(best), "bound": bound, "gap_pct": gap,
            "routes": routes, "wall_s": wall, "time_limit_s": limit}
