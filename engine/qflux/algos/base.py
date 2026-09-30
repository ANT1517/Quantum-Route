"""Frozen optimizer protocol (master doc §5.2)."""
from typing import Callable, Protocol

import numpy as np

from qflux.types import Solution

# callback(event: dict) every 5 iterations: {"iter", "evals", "best_F", "elapsed_s"}
ProgressCallback = Callable[[dict], None]
StopFlag = Callable[[], bool]


class Optimizer(Protocol):
    name: str

    def run(self, ev, budget_evals: int | None, budget_s: float | None,
            rng: np.random.Generator, callback: ProgressCallback | None = None,
            should_stop: StopFlag | None = None,
            init_keys: np.ndarray | None = None) -> tuple[Solution, list[tuple[int, float]]]:
        ...
