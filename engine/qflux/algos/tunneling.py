"""Quantum-tunneling escape (§7.6). Acceptance decays with width x sqrt(barrier height), unlike SA's exp(-h/T)."""
import numpy as np


def random_move(perm: np.ndarray, rng) -> tuple[np.ndarray, int]:
    """Move a block of 1–3 consecutive customers to a random position of the giant tour."""
    n = len(perm)
    width = int(rng.integers(1, min(3, n - 1) + 1))
    i = int(rng.integers(0, n - width + 1))
    block = perm[i:i + width]
    rest = np.concatenate([perm[:i], perm[i + width:]])
    j = int(rng.integers(0, len(rest) + 1))
    while j == i and len(rest) > 0:
        j = int(rng.integers(0, len(rest) + 1))
    return np.concatenate([rest[:j], block, rest[j:]]), width


def tunnel(best_perm: np.ndarray, f0: float, ev, rng, trials: int = 30, kappa: float = 8.0):
    """Returns (candidate perm, its F, "improve" | "tunnel" | "none"). Each trial is one evaluation."""
    for _ in range(trials):
        cand, width = random_move(best_perm, rng)
        f = ev.fitness_perm(cand)
        if f < f0:
            return cand, f, "improve"
        h = (f - f0) / max(abs(f0), 1e-12)
        if rng.random() < np.exp(-kappa * width * np.sqrt(max(h, 0.0))):
            return cand, f, "tunnel"
    return None, None, "none"
