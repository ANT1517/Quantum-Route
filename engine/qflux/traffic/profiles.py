"""Time-of-day load-ratio profiles by road class (§6.4). Values are illustrative (simulated traffic)."""
import numpy as np

# Road-class groups used by the traffic model
ARTERIAL, SECONDARY, RESIDENTIAL = 0, 1, 2
GROUP_NAMES = ("arterial", "secondary", "residential")

SLOT_CENTERS = np.array([180.0, 420.0, 540.0, 780.0, 1050.0, 1200.0, 1380.0])  # minutes since midnight
SLOT_LABELS = ("03:00", "07:00", "09:00", "13:00", "17:30", "20:00", "23:00")

# rho[slot, group]: background volume / capacity
LOAD_RATIO = np.array([
    [0.30, 0.20, 0.10],
    [1.10, 0.90, 0.50],
    [1.50, 1.20, 0.70],
    [1.10, 0.90, 0.50],
    [1.55, 1.25, 0.75],
    [1.10, 0.90, 0.50],
    [0.50, 0.40, 0.20],
])

DAY = 1440.0


def slot_weights(t: float, centers: np.ndarray = SLOT_CENTERS) -> tuple[int, int, float]:
    """Return (s, s1, lam) so that value(t) = (1-lam)*M[s] + lam*M[s1]. Wraps around midnight."""
    S = len(centers)
    t = t % DAY
    if t < centers[0] or t >= centers[-1]:
        s, s1 = S - 1, 0
        span = centers[0] + DAY - centers[-1]
        lam = ((t - centers[-1]) % DAY) / span
        return s, s1, float(lam)
    s = int(np.searchsorted(centers, t, side="right") - 1)
    lam = (t - centers[s]) / (centers[s + 1] - centers[s])
    return s, s + 1, float(lam)


def nearest_slot(t: float, centers: np.ndarray = SLOT_CENTERS) -> int:
    d = np.abs(((centers - t % DAY) + DAY / 2) % DAY - DAY / 2)
    return int(np.argmin(d))


def load_ratio(t: float, group: np.ndarray) -> np.ndarray:
    """rho(t, class) with linear interpolation between slot centres; `group` is an int array."""
    s, s1, lam = slot_weights(t)
    row = (1 - lam) * LOAD_RATIO[s] + lam * LOAD_RATIO[s1]
    return row[group]
