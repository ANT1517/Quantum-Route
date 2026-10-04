"""Standard PSO baseline (§7.8): identical pipeline to QPSO except the update rule (Clerc–Kennedy constriction)."""
import numpy as np

from qflux.config import load_config

from .swarm import KeySwarm


class PSO(KeySwarm):
    name = "pso"

    def __init__(self, **params):
        cfg = load_config()["pso"]
        p = {**cfg, "init": "uniform", "ls_every": 0, **params}
        p.setdefault("memetic", bool(p["ls_every"]))      # PSO+LS: identical LS rule to QPSO (D28)
        super().__init__(**p)
        self.V = None

    def setup(self, n, rng):
        self.V = None

    def update(self, X, P, fP, fX, G, t, T_est, rng):
        p = self.p
        if self.V is None:
            self.V = np.zeros_like(X)
        r1, r2 = rng.random(X.shape), rng.random(X.shape)
        self.V = p["w"] * self.V + p["c1"] * r1 * (P - X) + p["c2"] * r2 * (G - X)
        vmax = float(p["vmax"])
        self.V = np.clip(self.V, -vmax, vmax)
        return X + self.V
