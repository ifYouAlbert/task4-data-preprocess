from collections.abc import Sequence
from math import isfinite
from statistics import quantiles


def get_spectrum_without_bg(signal: Sequence[float], background: Sequence[float]) -> list[float]:
    if len(signal) != len(background):
        raise ValueError("signal length must be equal background length")

    spectrum: list[float] = []
    for index, (signal_value, bg_value) in enumerate(zip(signal, background), start=1):
        if bg_value == 0:
            raise ValueError(f"Background == 0 at index={index}")
        spectrum.append((bg_value - signal_value) / bg_value)

    return spectrum


def clip_outliers_iqr(spectrum: Sequence[float]) -> list[float]:
    if not all(isfinite(value) for value in spectrum):
        raise ValueError
    if len(spectrum) < 2:
        return list(spectrum)

    q1, _, q3 = quantiles(spectrum, n=4, method="inclusive")
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    return [min(max(value, lower_bound), upper_bound) for value in spectrum]


def normalize_spectrum(spectrum: Sequence[float]) -> list[float]:
    if len(spectrum) == 0:
        return []
    if not all(isfinite(value) for value in spectrum):
        raise ValueError

    minimum = min(spectrum)
    value_range = max(spectrum) - minimum
    if value_range == 0:
        return [0.0] * len(spectrum)

    return [(value - minimum) / value_range for value in spectrum]


def get_spectrum(signal: Sequence[float], background: Sequence[float]) -> list[float]:
    return normalize_spectrum(clip_outliers_iqr(get_spectrum_without_bg(signal, background)))
