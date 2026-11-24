from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from parser.explosives_csv_parser import ExplosivesCsvParser, ParseOutput, ExplosivesMetadata
from analysis.preprocessing import get_spectrum
from show.plot_tools import show_plot, PlotLine


@dataclass
class ExclusionLine:
    parsed: ParseOutput
    signal_index: int
    color: str
    style: str


def compare_plots(lines: Sequence[ExclusionLine], p_output_path: Path, title: str) -> None:
    plot_lines: list[PlotLine] = []
    for line in lines:
        signal = line.parsed.data.signals[line.signal_index]
        background = line.parsed.data.background

        plot_lines.append(PlotLine(
            label=get_line_label(line.parsed.data.metadata, line.signal_index),
            values=get_spectrum(signal, background),
            style=line.style,
            color=line.color,
        ))
    show_plot(
        plot_lines,
        title=title,
        xlabel="Спектральные отсчеты",
        ylabel="Интенсивность, отн. ед.",
        output_path=p_output_path,
    )


def get_line_label(metadata: ExplosivesMetadata, signal_index: int) -> str:
    sample = metadata.sample_type.value
    if metadata.concentration_ng is not None:
        sample += f", {metadata.concentration_ng} нг"

    return f"{metadata.substance}, {sample}, {metadata.source_path.name}, S{signal_index}"


if __name__ == "__main__":
    def get_parsed(p_file: Path) -> ParseOutput:
        parsed = ExplosivesCsvParser.parse(p_file)
        if not parsed.success:
            raise ValueError(f"Error in \"{p_file}\"")
        return parsed

    def main() -> None:
        p_project = Path(__file__).parent.parent.parent
        p_data = p_project / "data_explosives"

        compare_plots(
            lines=[
                ExclusionLine(
                    parsed=get_parsed(p_data / "Гексоген" / "Растворы" / "2500нг" / "1.csv"),
                    signal_index=0,
                    color="C0",
                    style="-",
                ),
                ExclusionLine(
                    parsed=get_parsed(p_data / "Гексоген" / "Палец" / "Концентрация не задана" / "1.csv"),
                    signal_index=0,
                    color="C1",
                    style="-",
                ),
            ],
            p_output_path=p_project / "output" / "plots" / "compare.png",
            title="Сравнение"
        )

    main()

