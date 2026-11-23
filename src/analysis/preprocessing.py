from collections.abc import Sequence


def get_spectrum_without_bg(signal: Sequence[float], background: Sequence[float]) -> list[float]:
    if len(signal) != len(background):
        raise ValueError("signal length must be equal background length")

    spectrum: list[float] = []
    for index, (signal_value, bg_value) in enumerate(zip(signal, background), start=1):
        if bg_value == 0:
            raise ValueError(f"Background == 0 at index={index}")
        spectrum.append((bg_value - signal_value) / bg_value)

    return spectrum
