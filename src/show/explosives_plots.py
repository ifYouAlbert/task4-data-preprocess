from pathlib import Path

from parser.explosives_csv_parser import ExplosivesCsvParser, ParseOutput, ExplosivesMetadata
from analysis.preprocessing import get_spectrum_without_bg
from show.plot_tools import show_plot, PlotLine


def get_plot_title(metadata: ExplosivesMetadata, signal_index: int) -> str:
    sample = metadata.sample_type.value
    if metadata.concentration_ng is not None:
        sample += f", {metadata.concentration_ng} нг"

    return f"{metadata.substance} | {sample} | {metadata.source_path.name} | S{signal_index}"


def get_plot_file_name(metadata: ExplosivesMetadata, signal_index: int) -> str:
    sample = metadata.sample_type.value
    if metadata.concentration_ng is not None:
        sample += f"_{metadata.concentration_ng}ng"

    return f"{metadata.substance}_{sample}_{metadata.source_path.stem}_s{signal_index}".lower()


def save_plots(parsed: ParseOutput, output_dir: Path, signal_index: int) -> tuple[Path, Path]:
    data = parsed.data
    signal = data.signals[signal_index]
    background = data.background

    filename = get_plot_file_name(parsed.data.metadata, signal_index)
    title = get_plot_title(parsed.data.metadata, signal_index)

    p_raw_path = output_dir / f"{filename}_raw.png"
    p_corrected_path = output_dir / f"{filename}_spectrum.png"

    show_plot(
        [
            PlotLine(f"S{signal_index}", signal, "-", "C0"),
            PlotLine(f"Фон", background, "--", "C1"),
        ],
        title=title,
        xlabel="Спектральные отсчеты",
        ylabel="Интенсивность, отн. ед.",
        output_path=p_raw_path,
    )

    spectrum = get_spectrum_without_bg(signal, background)
    show_plot(
        [
            PlotLine(f"Спектр после коррекции фона", spectrum, "-", "C0"),
        ],
        title=title,
        xlabel="Спектральные отсчеты",
        ylabel="Интенсивность, отн. ед.",
        output_path=p_corrected_path,
    )

    return p_raw_path, p_corrected_path


if __name__ == "__main__":
    def main() -> None:
        p_project = Path(__file__).parent.parent.parent
        p_csv_path = p_project / "data_explosives" / "Гексоген" / "Растворы" / "2500нг" / "1.csv"

        parsed = ExplosivesCsvParser.parse(p_csv_path)
        if not parsed.success:
            raise ValueError(f"Error in \"{p_csv_path}\"")

        paths = save_plots(
            parsed,
            output_dir=p_project / "output" / "plots",
            signal_index=0
        )

        print(f"results saved to: \n{"".join([f"* {p}\n" for p in paths])}")

    main()
