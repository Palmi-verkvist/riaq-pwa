"""
CO2 decay analysis engine.
Adapted from University of Galway notebook (CO2_decay_ventilation_calculation.ipynb).

Column mapping from raw Stofa CSV → internal names:
  dtm          → DateTime
  co2, ppm     → CO2_ppm
  HouseNo.     → HouseNo
  RoomType     → RoomType  (passthrough)
  pm25, μg/m³  → PM25      (optional)
  ch2o, ppm    → CH2O      (optional)
  RetrofitStatus → RetrofitStatus (optional)
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import curve_fit
from scipy.signal import find_peaks

from .purge_detection import check_purge_ventilation
from .qc_filters import calculate_r_squared, check_monotonic_decay

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Column mapping
# ---------------------------------------------------------------------------

COLUMN_MAP: dict[str, str] = {
    "dtm": "DateTime",
    "co2, ppm": "CO2_ppm",
    "HouseNo.": "HouseNo",
    "RoomType": "RoomType",
    "pm25, μg/m³": "PM25",
    "ch2o, ppm": "CH2O",
    "RetrofitStatus": "RetrofitStatus",
}

REQUIRED_RAW_COLUMNS = {"dtm", "co2, ppm", "HouseNo."}

# ---------------------------------------------------------------------------
# QC parameters
# ---------------------------------------------------------------------------


@dataclass
class QCParams:
    # Baseline outdoor CO2
    ambient_co2: float = 420.0

    # Decay completeness
    min_final_co2: float = 500.0       # ppm — reject if decay ends too close to baseline
    min_decay_fraction: float = 0.63   # must decay ≥ 63% of starting elevation above ambient

    # Model fit quality
    min_r_squared: float = 0.70

    # Ventilation rate bounds
    min_ach: float = 0.05              # h⁻¹ — minimum reasonable ventilation
    max_ach_normal: float = 1.2        # h⁻¹ — purge detection threshold

    # Secondary purge check
    max_decay_rate: float = 500.0      # ppm/h — initial decay rate threshold

    # Monotonicity tolerance
    max_increases: int = 3             # allow up to N small increases during decay

    # Peak / window detection
    min_peak_above: float = 250.0      # peak must be ≥ this above ambient to qualify
    target_end_ppm: float = 500.0      # stop decay window once CO2 drops to this
    max_hours: float = 4.0             # maximum decay window length


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _make_decay_model(ambient: float):
    """Return an exponential decay function with a fixed ambient baseline."""
    def model(t: np.ndarray, C0: float, ACH: float) -> np.ndarray:
        return (C0 - ambient) * np.exp(-ACH * t) + ambient
    return model


def _find_decay_periods(day_df: pd.DataFrame, params: QCParams) -> list[pd.DataFrame]:
    """Identify CO2 decay windows for a single house-day."""
    day_df = day_df.sort_values("DateTime")
    co2 = day_df["CO2_ppm"].values.astype(float)

    co2_smooth = gaussian_filter1d(co2, sigma=1.5)
    peaks, _ = find_peaks(
        co2_smooth,
        height=params.ambient_co2 + params.min_peak_above,
        distance=15,  # ~75 min gap at 5-min intervals
    )

    periods: list[pd.DataFrame] = []
    for peak_idx in peaks:
        peak_time = day_df.iloc[peak_idx]["DateTime"]

        window_mask = (
            (day_df["DateTime"] >= peak_time)
            & (day_df["DateTime"] <= peak_time + pd.Timedelta(hours=params.max_hours))
        )
        window_df = day_df[window_mask].copy()
        if window_df.empty:
            continue

        below = window_df[window_df["CO2_ppm"] <= params.target_end_ppm]
        if not below.empty:
            decay_df = window_df[window_df["DateTime"] <= below.iloc[0]["DateTime"]].copy()
        else:
            decay_df = window_df.copy()

        if len(decay_df) >= 10:
            periods.append(decay_df)

    return periods


def _fit_decay(
    decay_df: pd.DataFrame,
    house: str,
    date: object,
    decay_num: int,
    params: QCParams,
) -> tuple[Optional[dict], Optional[dict]]:
    """
    Fit one decay period and apply QC filters.
    Returns (result, None) on pass or (None, rejection) on fail.
    """
    decay_df = decay_df.copy()
    decay_df["t_hours"] = (
        (decay_df["DateTime"] - decay_df["DateTime"].iloc[0])
        .dt.total_seconds()
        / 3600
    )

    co2 = decay_df["CO2_ppm"].values
    times = decay_df["t_hours"].values
    base = {"HouseNo": house, "Date": date, "DecayEvent": decay_num}

    if len(times) < 10 or (co2[0] - co2[-1]) < 50:
        return None, {**base, "Reason": "Insufficient decay amplitude"}

    model = _make_decay_model(params.ambient_co2)
    lb = [float(co2.min()) - 50, params.min_ach]
    ub = [float(co2.max()) + 50, 10.0]

    try:
        popt, _ = curve_fit(
            model,
            times,
            co2,
            p0=[co2[0], 0.5],
            bounds=(lb, ub),
            maxfev=10_000,
        )
    except RuntimeError:
        return None, {**base, "Reason": "Curve fit failed"}

    C0_fit, ACH_fit = popt
    predicted = model(times, C0_fit, ACH_fit)
    r2 = calculate_r_squared(co2, predicted)
    initial_decay_rate = ACH_fit * (C0_fit - params.ambient_co2)  # ppm/h

    C_start, C_end = co2[0], co2[-1]
    decay_fraction = (
        (C_start - C_end) / (C_start - params.ambient_co2)
        if C_start > params.ambient_co2
        else 0.0
    )

    if C_end < params.min_final_co2:
        return None, {**base, "Reason": f"Final CO₂ {C_end:.0f} ppm < {params.min_final_co2:.0f} ppm"}

    if decay_fraction < params.min_decay_fraction:
        return None, {**base, "Reason": f"Decay fraction {decay_fraction*100:.1f}% < {params.min_decay_fraction*100:.0f}%"}

    if r2 < params.min_r_squared:
        return None, {**base, "Reason": f"Poor fit R²={r2:.3f} < {params.min_r_squared}"}

    is_purge, purge_reason = check_purge_ventilation(
        ACH_fit, initial_decay_rate, params.max_ach_normal, params.max_decay_rate
    )
    is_monotonic = check_monotonic_decay(co2, params.max_increases)

    return {
        **base,
        "C0_ppm": round(C0_fit, 1),
        "C0_timestamp": decay_df.iloc[0]["DateTime"].strftime("%Y-%m-%d %H:%M"),
        "ACH_per_hour": round(ACH_fit, 3),
        "InitialDecayRate_ppm_h": round(initial_decay_rate, 1),
        "R_squared": round(r2, 3),
        "DecayFraction": round(decay_fraction, 2),
        "NumDataPoints": len(decay_df),
        "IsPurge": is_purge,
        "PurgeReason": purge_reason,
        "IsMonotonic": is_monotonic,
    }, None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def normalise_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map raw Stofa CSV column names to internal names and parse types.
    Raises ValueError if required columns are missing.
    """
    missing = REQUIRED_RAW_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.copy()
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})
    df["DateTime"] = pd.to_datetime(df["DateTime"], utc=True)
    df["CO2_ppm"] = pd.to_numeric(df["CO2_ppm"], errors="coerce")
    df = df.dropna(subset=["DateTime", "CO2_ppm"])
    df = df.sort_values(["HouseNo", "DateTime"]).reset_index(drop=True)
    df["Date"] = df["DateTime"].dt.date
    return df


def run_analysis(
    df: pd.DataFrame,
    params: Optional[QCParams] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run full ACH analysis on a normalised DataFrame.

    Parameters
    ----------
    df      : output of normalise_dataframe()
    params  : QCParams — uses defaults if None

    Returns
    -------
    results_df  : one row per accepted decay event
    rejected_df : one row per rejected decay event with Reason column
    """
    if params is None:
        params = QCParams()

    results: list[dict] = []
    rejected: list[dict] = []

    for house in df["HouseNo"].unique():
        house_df = df[df["HouseNo"] == house]
        for date in sorted(house_df["Date"].unique()):
            day_df = house_df[house_df["Date"] == date]
            for decay_num, decay_df in enumerate(_find_decay_periods(day_df, params), start=1):
                result, rejection = _fit_decay(decay_df, house, date, decay_num, params)
                if result is not None:
                    results.append(result)
                elif rejection is not None:
                    rejected.append(rejection)

    return pd.DataFrame(results), pd.DataFrame(rejected)
