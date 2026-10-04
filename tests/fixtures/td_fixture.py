"""Fake time-dependent instance built from CVRPLIB coordinates with random traffic multipliers per slot.

Used by engine tests so they do not depend on the Hyderabad cache (Person B's data)."""
import numpy as np

from qflux.bench.loader import load_instance
from qflux.types import Instance

CENTERS = np.array([180.0, 420.0, 540.0, 780.0, 1050.0, 1200.0, 1380.0])


def td_instance(name: str = "A-n32-k5", seed: int = 0, tau0: float = 1050.0, K: int | None = 5) -> Instance:
    base = load_instance(name)
    rng = np.random.default_rng(seed)
    D = base.D / 10.0                                  # "km"
    T0 = D / 30.0 * 60.0                               # minutes at 30 km/h
    S = len(CENTERS)
    mult = 1.0 + np.abs(rng.normal(0, 0.3, (S, 1, 1))) * rng.uniform(0.5, 1.5, (1,) + D.shape)
    mult = (mult + mult.transpose(0, 2, 1)) / 2
    T = T0[None] * mult
    E = D[None] * (0.15 + 0.05 * (mult - 1.0))
    return Instance(name=f"{name}-td", source="synth", n=base.n, Q=base.Q, K=K, demand=base.demand,
                    service=np.r_[0.0, np.full(base.n, 5.0)], coords=base.coords, D=D, slot_centers=CENTERS,
                    T_slots=T, T0=T0, D_slots=np.repeat(D[None], S, 0), E_slots=E, tau0=tau0)
