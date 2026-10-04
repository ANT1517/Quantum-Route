"""Bench tests T08–T09 (§10.1)."""
import dataclasses
import json

import numpy as np
import pytest
from scipy import stats as sps

from qflux.bench import stats
from qflux.bench.harness import read_records, resample_curve, run_experiment, run_seed
from qflux.types import RunRecord


def test_t08_harness_smoke(tmp_path):
    exp = {"name": "t08", "instances": ["P-n16-k8"], "runs": 2, "weights": [0, 1, 0, 0],
           "budgets": [{"type": "evals", "value": 400, "algorithms": ["qpso", "ga"]}]}
    path = run_experiment(exp, out_dir=tmp_path, log=lambda *_: None, workers=2)    # parallel path (D30)
    recs = read_records(path)
    assert len(recs) == 4
    fields = [f.name for f in dataclasses.fields(RunRecord)]
    for r in recs:
        assert list(r) == fields
        assert r["evals_used"] >= 400 and r["gap_pct"] is not None and r["best_D"] > 0
        assert r["curve"][-1][0] == r["evals_used"]
        assert all(b[1] <= a[1] + 1e-12 for a, b in zip(r["curve"], r["curve"][1:]))   # best-so-far
    assert {r["seed"] for r in recs} == {run_seed("P-n16-k8", 0), run_seed("P-n16-k8", 1)}
    assert all("ls_calls" in r["meta"] for r in recs)
    # resume: nothing is re-run
    run_experiment(exp, out_dir=tmp_path, log=lambda *_: None, workers=1)
    assert len(read_records(path)) == 4
    json.dumps(recs)


def test_t09_wilcoxon_matches_scipy():
    rng = np.random.default_rng(9)
    a = rng.normal(10, 1, 15)
    b = a + rng.normal(0.5, 0.3, 15)
    ref = sps.wilcoxon(a, b)
    stat, p = stats.wilcoxon_pair(a, b)
    assert stat == pytest.approx(ref.statistic) and p == pytest.approx(ref.pvalue)
    assert stats.wilcoxon_pair(a, a.copy()) == (0.0, 1.0)


def test_resample_curve_every_100():
    c = resample_curve([(40, 5.0), (80, 4.0), (250, 3.0), (330, 2.5)], 330, 2.4)
    assert c == [(100, 4.0), (200, 4.0), (300, 3.0), (330, 2.4)]


def test_seed_formula():
    assert run_seed("A-n32-k5", 2, 12345) == 12345 + 1000 * 3 + 2


def test_rank_normalise_keeps_tours():
    from qflux.algos.swarm import rank_normalise
    from qflux.core.encoding import spv_decode
    X = np.random.default_rng(3).normal(0, 1e4, (6, 30))
    Z = rank_normalise(X)
    assert (Z > 0).all() and (Z < 1).all()
    for x, z in zip(X, Z):
        assert (spv_decode(x) == spv_decode(z)).all()


@pytest.mark.parametrize("algo", ["qpso", "pso_ls", "ga_ls", "sa", "rr_ls", "ortools"])
def test_deadline_respected(algo):
    """D31: wall time stays within the time budget (+2% in the benchmark; looser here for CI jitter)."""
    import time
    from qflux.algos.registry import get_optimizer
    from qflux.bench.loader import load_instance
    from qflux.core.evaluate import Evaluator
    from qflux.rng import make_rng
    from qflux.types import Weights
    inst = load_instance("A-n63-k9")
    ev = Evaluator(inst, Weights(wT=0, wD=1))
    get_optimizer(algo).run(Evaluator(inst, Weights(wT=0, wD=1)), 200, None, make_rng(0))   # JIT warm-up
    t = time.time()
    sol, _ = get_optimizer(algo).run(ev, None, 2.0, make_rng(1))
    assert time.time() - t <= 2.0 * 1.05
    if algo in ("qpso", "pso_ls", "ga_ls", "rr_ls"):
        assert sol.meta["ls_calls"] > 0


def test_cluster_qpso_feasible():
    """D47: cluster-first QPSO returns a feasible solution covering every customer within the time budget."""
    import time
    from qflux.algos.registry import get_optimizer
    from qflux.bench.loader import load_instance
    from qflux.core.evaluate import Evaluator
    from qflux.core.feasibility import check
    from qflux.rng import make_rng
    from qflux.types import Weights
    inst = load_instance("X-n502-k39")
    ev = Evaluator(inst, Weights(wT=0, wD=1))
    t = time.time()
    sol, _ = get_optimizer("qpso_cluster").run(ev, None, 8.0, make_rng(5))
    assert time.time() - t <= 8.0 * 1.05
    assert check(inst, sol, ev)[0]
    assert len(sol.meta["clusters"]) == 5 and sum(c["size"] for c in sol.meta["clusters"]) == inst.n
