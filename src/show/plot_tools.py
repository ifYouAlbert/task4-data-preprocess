from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt


@dataclass
class PlotLine:
    label: str
    values: Sequence[float]
    style: str
    color: str


def show_plot(
    lines: Sequence[PlotLine],
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    output_path: Path | None = None,
) -> None:
    figure, axes = plt.subplots(figsize=(8, 4.5), layout="constrained")
    try:
        for plot_line in lines:
            axes.plot(
                range(1, len(plot_line.values) + 1),
                plot_line.values,
                linestyle=plot_line.style,
                label=plot_line.label,
                color=plot_line.color
            )

        axes.set(title=title, xlabel=xlabel, ylabel=ylabel)
        axes.grid(alpha=0.25)
        axes.legend()

        if output_path is None:
            plt.show()
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            figure.savefig(output_path, dpi=160)
    finally:
        plt.close(figure)
