"""Reference MILP for small static CVRP (§3.2): two-index formulation with MTZ load constraints, PuLP/CBC."""
import time

import numpy as np

from qflux.config import load_config


def solve_milp(inst, time_limit_s: float | None = None, K: int | None = None, msg: bool = False) -> dict:
    import pulp
    cfg = load_config()["milp"]
    if inst.n > cfg["max_n"]:
        raise ValueError(f"MILP limited to n <= {cfg['max_n']}")
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
    t = time.time()
    status = prob.solve(pulp.PULP_CBC_CMD(msg=msg, timeLimit=time_limit_s or cfg["time_limit_s"]))
    wall = time.time() - t
    succ = {i: j for (i, j), var in x.items() if var.value() is not None and var.value() > 0.5}
    routes = []
    for j in cust:
        if succ.get(0) is None:
            break
    for (i, j), var in x.items():
        if i == 0 and var.value() is not None and var.value() > 0.5:
            r, cur = [], j
            while cur != 0:
                r.append(cur)
                cur = succ[cur]
            routes.append(r)
    return {"status": pulp.LpStatus[status], "optimal": pulp.LpStatus[status] == "Optimal" and wall < (time_limit_s or cfg["time_limit_s"]),
            "objective": float(pulp.value(prob.objective)), "bound": None, "routes": routes, "wall_s": wall}
