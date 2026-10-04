"""Where does a QPSO-full run spend its wall time? (measurement only; no configuration change)

    python scripts/profile_qpso.py [--instance A-n80-k10] [--time-s 30] [--seed 1]

Wraps the existing methods with timers and reports the share of wall time in: swarm update (position update +
rank re-normalisation), decode + Split evaluation, memetic LS, gbest LS, tunneling, QUBO slot, diversity
re-init / bookkeeping (other), final polish. Writes results/tables/profile_qpso_<instance>.json.
Run on an otherwise idle machine.
"""
import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

from qflux.algos import qpso as qpso_mod  # noqa: E402
from qflux.algos import swarm as swarm_mod  # noqa: E402
from qflux.algos.qpso import QPSO  # noqa: E402
from qflux.bench.harness import machine_info, warm_up  # noqa: E402
from qflux.bench.loader import load_instance  # noqa: E402
from qflux.core.evaluate import Evaluator  # noqa: E402
from qflux.rng import make_rng  # noqa: E402
from qflux.types import Weights  # noqa: E402

T = defaultdict(float)
N = defaultdict(int)


def timed(label, fn):
    def wrapper(*a, **k):
        t = time.perf_counter()
        try:
            return fn(*a, **k)
        finally:
            T[label] += time.perf_counter() - t
            N[label] += 1
    return wrapper


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", default="A-n80-k10")
    ap.add_argument("--time-s", type=float, default=30.0)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    inst = load_instance(a.instance)
    warm_up(["qpso"], a.instance)
    # timers (patched on the classes/modules the run uses)
    QPSO.update = timed("swarm_update", QPSO.update)
    swarm_mod.rank_normalise = timed("swarm_update", swarm_mod.rank_normalise)
    swarm_mod.State.eval_keys = timed("decode_split_eval", swarm_mod.State.eval_keys)
    swarm_mod.KeySwarm.memetic_positions = timed("memetic_ls", swarm_mod.KeySwarm.memetic_positions)
    swarm_mod.KeySwarm.polish = timed("gbest_ls", swarm_mod.KeySwarm.polish)
    qpso_mod.tunnel = timed("tunneling", qpso_mod.tunnel)
    QPSO.qubo_slot = timed("qubo_slot", QPSO.qubo_slot)
    orig_final = QPSO.final_polish

    def final_polish(self, st, ev, rng):          # time the final LS only; its QUBO part goes to qubo_slot
        q0, t = T["qubo_slot"], time.perf_counter()
        orig_final(self, st, ev, rng)
        T["final_polish_ls"] += (time.perf_counter() - t) - (T["qubo_slot"] - q0)
        N["final_polish_ls"] += 1
    QPSO.final_polish = final_polish
    ev = Evaluator(inst, Weights(wT=0, wD=1))
    t0 = time.perf_counter()
    sol, _ = QPSO().run(ev, None, a.time_s, make_rng(a.seed))
    wall = time.perf_counter() - t0
    parts = {k: T[k] for k in ("swarm_update", "decode_split_eval", "memetic_ls", "gbest_ls", "tunneling", "qubo_slot",
                               "final_polish_ls")}
    parts["other"] = max(0.0, wall - sum(parts.values()))
    out = {"instance": a.instance, "time_budget_s": a.time_s, "seed": a.seed, "wall_s": wall,
           "iterations": sol.meta.get("iterations"), "evals": ev.evals, "ls_calls": sol.meta.get("ls_calls"),
           "qubo_calls": sol.meta.get("qubo_calls"), "tunnel_events": len(sol.meta.get("tunnel_events", [])),
           "seconds": parts, "share_pct": {k: 100 * v / wall for k, v in parts.items()},
           "calls": dict(N), "machine": machine_info(),
           "note": "Measurement only, one run; not a benchmark. QUBO time inside the final polish is counted under qubo_slot."}
    path = ROOT / "results" / "tables" / f"profile_qpso_{a.instance}.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    for k, v in out["share_pct"].items():
        print(f"{k:24s} {v:5.1f}%  ({parts[k]:.2f} s)")
    print(f"iterations {out['iterations']}, evals {ev.evals}, ls_calls {out['ls_calls']}, qubo_calls {out['qubo_calls']}; wrote {path}")


if __name__ == "__main__":
    main()
