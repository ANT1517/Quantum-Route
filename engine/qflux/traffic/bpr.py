"""BPR link performance and marginal cost (§6.4, §6.6.1). a, b are the BPR parameters (not QPSO alpha)."""
import numpy as np

A_BPR, B_BPR = 0.15, 4.0


def bpr_time(t0, volume, capacity, a: float = A_BPR, b: float = B_BPR):
    """t_e = t0 * [1 + a * (v / C)^b]"""
    return t0 * (1.0 + a * (volume / capacity) ** b)


def marginal_cost(t0, volume, capacity, a: float = A_BPR, b: float = B_BPR):
    """mc_e = t_e(v) + v * dt_e/dv = t0 * [1 + a * (1 + b) * (v / C)^b]"""
    return t0 * (1.0 + a * (1.0 + b) * (volume / capacity) ** b)
