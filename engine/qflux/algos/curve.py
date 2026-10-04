"""Wall-time convergence curve (D40): (elapsed_s, best_F) at every improvement plus the final point.

Stored in Solution.meta["curve_t"] / RunRecord.meta["curve_t"]; time-budget convergence plots use it
(the evaluation-indexed `curve` stays for evaluation-budget runs).
"""
import time

import numpy as np


class TimeCurve:
    def __init__(self, t0: float | None = None):
        self.t0 = time.time() if t0 is None else t0
        self.best = np.inf
        self.pts: list[tuple[float, float]] = []

    def add(self, f: float, at: float | None = None):
        if f < self.best - 1e-12:
            self.best = float(f)
            self.pts.append((round((time.time() if at is None else at) - self.t0, 4), self.best))

    def final(self, f: float) -> list[tuple[float, float]]:
        self.add(f)
        el = round(time.time() - self.t0, 4)
        if not self.pts or self.pts[-1][0] < el:
            self.pts.append((el, self.best))
        return self.pts
