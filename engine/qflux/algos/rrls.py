"""RR+LS control (D34): random restarts + local search, an ablation row, not a headline row.

Every iteration draws fresh uniform random keys for the whole swarm, then runs exactly the same pipeline as
QPSO-full: Split decoding, the same memetic LS rule (D33), gbest LS every `ls_every` iterations, Lamarckian
write-back, the same budgets and deadlines. The only thing missing is a position-update rule, so
QPSO-full vs RR+LS answers "does the QPSO update add value beyond LS?".
"""
from qflux.config import load_config

from .swarm import KeySwarm


class RRLS(KeySwarm):
    name = "rr_ls"
    defaults = {"memetic": True}

    def __init__(self, **params):
        q = load_config()["qpso"]
        super().__init__(**{"N": q["N"], "init": "uniform", "ls_every": q["ls_every"], "lamarck": q["lamarck"],
                            **params})

    def update(self, X, P, fP, fX, G, t, T_est, rng):
        return rng.random(X.shape)
