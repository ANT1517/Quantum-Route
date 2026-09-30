"""Illustrative COPERT-shaped speed–emission curve (§6.7). Calibration is finale work."""
import numpy as np


def co2_g_per_km(v_kmh):
    v = np.maximum(v_kmh, 5.0)
    return 200 + 3000 / v - 2.5 * v + 0.02 * v ** 2


def edge_co2_kg(length_km, time_min):
    """CO2 (kg) for traversing an edge of length_km in time_min."""
    v = length_km / np.maximum(time_min, 1e-9) * 60.0
    return co2_g_per_km(v) * length_km / 1000.0
