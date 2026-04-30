"""
Synthetic-data tests for the decay engine.
Run with: python -m pytest tests/ -v
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analysis.decay_engine import QCParams, normalise_dataframe, run_analysis
from analysis.qc_filters import calculate_r_squared, check_monotonic_decay
from analysis.purge_detection import check_purge_ventilation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_synthetic_csv(
    house: str = "TEST_001",
    ach: float = 0.4,
    c0: float = 1800.0,
    ambient: float = 420.0,
    n_decay: int = 48,     # decay-window points (4 hours at 5-min intervals)
    n_pre: int = 12,       # ambient pre-period points (1 hour)
    n_rise: int = 6,       # ramp-up to peak (30 min)
    interval_min: int = 5,
    noise_std: float = 10.0,
    start: str = "2026-02-09 08:00:00+00:00",
) -> pd.DataFrame:
    """
    Return a DataFrame in raw Stofa column format with one clean rise-then-decay period.
    The pre + rise section ensures find_peaks can detect the peak at the start of decay.
    """
    rng = np.random.default_rng(42)
    n_total = n_pre + n_rise + n_decay
    times = pd.date_range(start=start, periods=n_total, freq=f"{interval_min}min", tz="UTC")

    pre = np.full(n_pre, ambient) + rng.normal(0, noise_std / 2, n_pre)
    rise = np.linspace(ambient, c0, n_rise) + rng.normal(0, noise_std / 2, n_rise)
    t = np.arange(n_decay) * (interval_min / 60)
    decay = (c0 - ambient) * np.exp(-ach * t) + ambient + rng.normal(0, noise_std, n_decay)

    co2 = np.clip(np.concatenate([pre, rise, decay]), ambient, None)

    return pd.DataFrame({
        "HouseNo.": house,
        "dtm": times.strftime("%d-%b-%Y %H:%M:%S+00:00"),
        "co2, ppm": co2.round().astype(int),
        "RoomType": "Living room",
    })


# ---------------------------------------------------------------------------
# normalise_dataframe
# ---------------------------------------------------------------------------


def test_normalise_renames_columns():
    raw = make_synthetic_csv()
    df = normalise_dataframe(raw)
    assert "DateTime" in df.columns
    assert "CO2_ppm" in df.columns
    assert "HouseNo" in df.columns
    assert "Date" in df.columns


def test_normalise_raises_on_missing_required():
    raw = make_synthetic_csv().drop(columns=["co2, ppm"])
    with pytest.raises(ValueError, match="Missing required columns"):
        normalise_dataframe(raw)


def test_normalise_drops_unnamed():
    raw = make_synthetic_csv()
    raw["Unnamed: 0"] = range(len(raw))
    df = normalise_dataframe(raw)
    assert not any(c.startswith("Unnamed") for c in df.columns)


# ---------------------------------------------------------------------------
# QC helpers
# ---------------------------------------------------------------------------


def test_r_squared_perfect():
    arr = np.array([1.0, 2.0, 3.0, 4.0])
    assert calculate_r_squared(arr, arr) == pytest.approx(1.0)


def test_r_squared_constant_observed():
    arr = np.array([5.0, 5.0, 5.0])
    assert calculate_r_squared(arr, arr) == 0.0


def test_monotonic_decay_passes():
    # 3 small increases in a long downward series
    vals = np.array([1000, 980, 990, 960, 940, 950, 920, 900, 910, 880], dtype=float)
    assert check_monotonic_decay(vals, max_increases=3)


def test_monotonic_decay_fails():
    vals = np.array([1000, 980, 990, 970, 980, 960, 970, 950, 960, 940], dtype=float)
    assert not check_monotonic_decay(vals, max_increases=3)


# ---------------------------------------------------------------------------
# Purge detection
# ---------------------------------------------------------------------------


def test_purge_detected_by_ach():
    is_purge, reason = check_purge_ventilation(1.5, 300.0)
    assert is_purge
    assert "ACH" in reason


def test_purge_detected_by_decay_rate():
    is_purge, reason = check_purge_ventilation(0.8, 600.0)
    assert is_purge
    assert "Decay rate" in reason


def test_no_purge():
    is_purge, reason = check_purge_ventilation(0.3, 200.0)
    assert not is_purge
    assert reason is None


# ---------------------------------------------------------------------------
# run_analysis — end-to-end with synthetic data
# ---------------------------------------------------------------------------


def test_run_analysis_recovers_ach():
    """Engine should recover a known ACH ≈ 0.4 from clean synthetic data."""
    true_ach = 0.4
    raw = make_synthetic_csv(ach=true_ach, noise_std=5.0)
    df = normalise_dataframe(raw)
    results, rejected = run_analysis(df)

    assert len(results) >= 1, f"Expected ≥1 accepted event, got 0. Rejected: {rejected}"
    estimated = results["ACH_per_hour"].iloc[0]
    assert abs(estimated - true_ach) < 0.15, f"ACH estimate {estimated:.3f} too far from {true_ach}"


def test_run_analysis_rejects_flat_signal():
    """A flat CO2 signal (no decay) should produce zero results."""
    rng = np.random.default_rng(0)
    times = pd.date_range("2026-02-09 08:00+00:00", periods=48, freq="5min", tz="UTC")
    raw = pd.DataFrame({
        "HouseNo.": "FLAT_001",
        "dtm": times.strftime("%d-%b-%Y %H:%M:%S+00:00"),
        "co2, ppm": (500 + rng.normal(0, 5, 48)).round().astype(int),
        "RoomType": "Office",
    })
    df = normalise_dataframe(raw)
    results, _ = run_analysis(df)
    assert len(results) == 0


def test_run_analysis_returns_dataframes():
    raw = make_synthetic_csv()
    df = normalise_dataframe(raw)
    results, rejected = run_analysis(df)
    assert isinstance(results, pd.DataFrame)
    assert isinstance(rejected, pd.DataFrame)


def test_run_analysis_purge_flagged_not_rejected():
    """High-ACH event (purge) should appear in results with IsPurge=True, not in rejected."""
    # Very fast decay → ACH well above 1.2
    raw = make_synthetic_csv(ach=2.5, c0=2500.0, noise_std=5.0)
    df = normalise_dataframe(raw)
    params = QCParams(min_final_co2=400.0)  # relax filter so purge event isn't rejected early
    results, _ = run_analysis(df, params)
    purges = results[results["IsPurge"]]
    assert len(purges) >= 1, "Expected at least one purge-tagged result"
