from collections import Counter
from collections.abc import Sequence
from math import sqrt
from pathlib import Path
from statistics import fmean, median, pvariance

from pydantic import BaseModel

from parser.explosives_csv_parser import ExplosivesMetadata


class DescriptiveStatistics(BaseModel):
    mean: float
    median: float
    modes: list[int | float]
    value_range: int | float
    mean_absolute_deviation: float
    variance: float
    standard_deviation: float
    coefficient_of_variation_percent: float | None


class FileSummary(BaseModel):
    metadata: ExplosivesMetadata
    signals: dict[str, DescriptiveStatistics]
    background: DescriptiveStatistics | None = None


class AnalysisOutput(BaseModel):
    files_analyzed: int
    files_skipped: int
    signal_count: int
    files: list[FileSummary]


def describe_series(values: Sequence[int | float]) -> DescriptiveStatistics:
    average = fmean(values)
    variance = pvariance(values)
    standard_deviation = sqrt(variance)

    frequencies = Counter(values)
    highest_frequency = max(frequencies.values())
    modes = []
    if highest_frequency > 1:
        modes = sorted(value for value, count in frequencies.items() if count == highest_frequency)

    return DescriptiveStatistics(
        mean=average,
        median=median(values),
        modes=modes,
        value_range=max(values) - min(values),
        mean_absolute_deviation=fmean(abs(value - average) for value in values),
        variance=variance,
        standard_deviation=standard_deviation,
        coefficient_of_variation_percent=100 * standard_deviation / average if average else None,
    )


def analyze_file(
    signals: Sequence[Sequence[int | float]],
    metadata: ExplosivesMetadata,
    background: Sequence[int | float] | None = None,
) -> FileSummary:
    return FileSummary(
        metadata=metadata,
        signals={f"S{index}": describe_series(signal) for index, signal in enumerate(signals)},
        background=describe_series(background) if background is not None else None,
    )


if __name__ == "__main__":
    from parser.explosives_csv_parser import ExplosivesCsvParser
    from analysis.preprocessing import get_spectrum

    def main() -> None:
        p_project = Path(__file__).parent.parent.parent
        p_data = p_project / "data_explosives"

        p_output = p_project / "output" / "analysis"
        p_analysis_for_raw_out = p_output / "analysis_for_raw.json"
        p_analysis_for_preprocess_out = p_output / "analysis_for_preprocess.json"

        files: list[FileSummary] = []
        files_preprocess: list[FileSummary] = []
        files_skipped = 0
        for p in p_data.rglob("*.csv"):
            out = ExplosivesCsvParser.parse(p)
            if not out.success:
                print(f"Error in \"{p.relative_to(p_data)}\". Skipping")
                files_skipped += 1
                continue

            data = out.data
            files.append(analyze_file(data.signals, data.metadata, data.background))
            files_preprocess.append(analyze_file(
                [get_spectrum(signal, data.background) for signal in data.signals],
                data.metadata,
            ))

        result = AnalysisOutput(
            files_analyzed=len(files),
            files_skipped=files_skipped,
            signal_count=sum(len(file.signals) for file in files),
            files=files,
        )
        result_preprocess = AnalysisOutput(
            files_analyzed=len(files_preprocess),
            files_skipped=files_skipped,
            signal_count=sum(len(file.signals) for file in files_preprocess),
            files=files_preprocess,
        )

        p_output.mkdir(parents=True, exist_ok=True)
        p_analysis_for_raw_out.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        p_analysis_for_preprocess_out.write_text(result_preprocess.model_dump_json(indent=2), encoding="utf-8")
        print(f"Saved to \"{p_analysis_for_raw_out}\" and \"{p_analysis_for_preprocess_out}\".")

    main()
