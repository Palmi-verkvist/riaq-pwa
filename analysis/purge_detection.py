from __future__ import annotations


def check_purge_ventilation(
    ach_fit: float,
    initial_decay_rate: float,
    max_ach_normal: float = 1.2,
    max_decay_rate: float = 500.0,
) -> tuple[bool, str | None]:
    """
    Returns (is_purge, reason_string).
    Purge events are tagged, not rejected — they appear in results with IsPurge=True.
    """
    if ach_fit > max_ach_normal:
        return True, f"ACH {ach_fit:.3f} h⁻¹ > {max_ach_normal} h⁻¹"
    if initial_decay_rate > max_decay_rate:
        return True, f"Decay rate {initial_decay_rate:.0f} ppm/h > {max_decay_rate} ppm/h"
    return False, None
