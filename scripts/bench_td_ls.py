"""D46 speed check on Hyderabad-60: generic TD local search vs static-proxy LS with TD verification.

    python scripts/bench_td_ls.py [--tours 100]

Same random giant tours (fixed seed), memetic operator set (2-opt + relocate + swap), balanced weights.
Reports median/p90 time per LS call and the true time-dependent cost after LS (mean ratio proxy/generic),
because D46 is not move-for-move identical to the generic kernel. Writes results/tables/d46_td_ls_speed.csv.
Run on an idle machine.
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from qflux import api as engine  # noqa: E402
from qflux.core.evaluate import Evaluator  # noqa: E402
from qflux.core.localsearch import MEMETIC_OPS, improve_routes  # noqa: E402
from qflux.traffic.route_eval import compute_refs  # noqa: E402
from qflux.traffic.td_matrix import bundle_for  # noqa: E402

SPEC = {"source": "hyderabad", "n_customers": 60, "K": 6, "Q": 200, "seed": 7, "tau0": 1050}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tours", type=int, default=100)
    a = ap.parse_args()
    inst = engine.build_instance(SPEC)
    w = engine.weights_from({"wT": 0.5, "wD": 0.2, "wC": 0.2, "wE": 0.1})
    ev = Evaluator(inst, w, compute_refs(inst, bundle_for(inst)))
    rng = np.random.default_rng(46)
    tours = [ev.decode_routes(rng.permutation(inst.n) + 1) for _ in range(a.tours)]
    for mode in (False, True):                       # warm-up / JIT compile
        improve_routes(tours[0], ev, MEMETIC_OPS, td_proxy=mode)
    rows = []
    for k, routes in enumerate(tours):
        before = ev.routes_F(routes)
        for mode in (False, True):
            t = time.perf_counter()
            out = improve_routes(routes, ev, MEMETIC_OPS, td_proxy=mode)
            dt = time.perf_counter() - t
            rows.append({"tour": k, "mode": "proxy_td_verified" if mode else "generic_td", "ms": 1e3 * dt,
                         "F_before": before, "F_after": ev.routes_F(out)})
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "results" / "tables" / "d46_td_ls_speed.csv", index=False, float_format="%.6g")
    s = df.groupby("mode").agg(median_ms=("ms", "median"), p90_ms=("ms", lambda x: x.quantile(0.9)),
                               mean_F_after=("F_after", "mean"))
    piv = df.pivot(index="tour", columns="mode", values="F_after")
    print(s.round(3).to_string())
    print(f"speedup (median generic / median proxy): {s.loc['generic_td', 'median_ms'] / s.loc['proxy_td_verified', 'median_ms']:.1f}x")
    print(f"TD cost after LS, proxy / generic: mean {np.mean(piv.proxy_td_verified / piv.generic_td):.4f}, "
          f"proxy better on {int((piv.proxy_td_verified < piv.generic_td - 1e-12).sum())}, "
          f"worse on {int((piv.proxy_td_verified > piv.generic_td + 1e-12).sum())} of {len(piv)} tours")


if __name__ == "__main__":
    main()
