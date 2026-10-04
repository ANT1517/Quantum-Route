"""D46: static-proxy LS with TD verification on time-dependent instances.

Guarantees tested: never returns a worse time-dependent cost than its input; every route stays capacity
feasible and every customer is served exactly once (0 infeasible). Speed vs the generic TD kernel is reported
by scripts/bench_td_ls.py, not asserted here (machine dependent).
"""
import numpy as np
import pytest

from qflux.core.evaluate import Evaluator
from qflux.core.feasibility import quick_feasible
from qflux.core.localsearch import MEMETIC_OPS, OPS, improve_routes
from qflux.types import Weights

from ..fixtures.td_fixture import td_instance

W = Weights(wT=0.5, wD=0.2, wC=0.2, wE=0.1)


@pytest.mark.parametrize("ops", ["memetic", "all"])
def test_td_proxy_never_worse_and_feasible(ops):
    inst = td_instance("A-n44-k6", seed=3, K=None)
    ev = Evaluator(inst, W)
    op_set = MEMETIC_OPS if ops == "memetic" else OPS
    rng = np.random.default_rng(46)
    for _ in range(100):
        routes = ev.decode_routes(rng.permutation(inst.n) + 1)
        before = ev.routes_F(routes)
        after_routes = improve_routes(routes, ev, op_set, td_proxy=True)
        assert quick_feasible(inst, after_routes)
        assert ev.routes_F(after_routes) <= before + 1e-12


def test_td_proxy_off_uses_generic_kernel():
    """td_proxy=False must give exactly the generic kernel's result (unchanged behaviour when disabled)."""
    inst = td_instance("A-n32-k5", seed=1, K=None)
    ev = Evaluator(inst, W)
    rng = np.random.default_rng(7)
    routes = ev.decode_routes(rng.permutation(inst.n) + 1)
    a = improve_routes(routes, ev, OPS, td_proxy=False)
    b = improve_routes(routes, ev, OPS, fast=False)
    assert a == b
