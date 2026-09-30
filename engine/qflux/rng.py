"""Seeded RNG helper. Never use global random state."""
import numpy as np


def make_rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)
