from __future__ import annotations

import numpy as np


def calculate_r_squared(observed: np.ndarray, predicted: np.ndarray) -> float:
    ss_res = np.sum((observed - predicted) ** 2)
    ss_tot = np.sum((observed - np.mean(observed)) ** 2)
    if ss_tot == 0:
        return 0.0
    return float(1 - (ss_res / ss_tot))


def check_monotonic_decay(co2_vals: np.ndarray, max_increases: int = 3) -> bool:
    increases = sum(1 for i in range(1, len(co2_vals)) if co2_vals[i] > co2_vals[i - 1])
    return increases <= max_increases
