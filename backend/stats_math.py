"""Shared statistics helpers for comparing a measurement against a reference
population. Used by analysis.py (web app percentiles) and preprocess.py
(batch outlier analysis)."""
from math import erf, sqrt


def zscore_to_percentile(value: float, mean: float, std: float) -> float:
    """Percentile of `value` in a normal distribution with the given mean/std.

    A degenerate reference (std == 0, e.g. a single-subject comparison)
    returns 0.5 rather than dividing by zero.
    """
    if std == 0:
        return 0.5
    z = (value - mean) / std
    return 0.5 * (1 + erf(z / sqrt(2)))
