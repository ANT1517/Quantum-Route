"""Random-key encoding (§7.1). No clipping: only the order of keys matters (D16)."""
import numpy as np


def spv_decode(keys: np.ndarray) -> np.ndarray:
    return np.argsort(keys, kind="stable") + 1


def encode_perm(perm: np.ndarray, rng, jitter: float = 0.1) -> np.ndarray:
    perm = np.asarray(perm)
    n = len(perm)
    keys = np.empty(n)
    keys[perm - 1] = (np.arange(n) + jitter * rng.random(n)) / n
    return keys
