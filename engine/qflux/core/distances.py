"""Distance conventions (§11.2): nint(Euclidean) for Augerat/Uchoa, exact Euclidean for CMT."""
import numpy as np


def euclidean(coords: np.ndarray, convention: str = "exact") -> np.ndarray:
    d = np.sqrt(((coords[:, None, :] - coords[None, :, :]) ** 2).sum(-1))
    if convention == "nint":
        d = np.floor(d + 0.5)
    return d
