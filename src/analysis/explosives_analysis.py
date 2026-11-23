from collections import Counter
from math import sqrt
from pathlib import Path
from statistics import fmean, median, pvariance

from pydantic import BaseModel

from parser.explosives_csv_parser import (
    ExplosivesCsvParser,
    ExplosivesMetadata,
    ParsedSectionStats,
    ParseOutput,
)


class DescriptiveStatistics(BaseModel):
    mean: float
    median: float
    modes: list[int]
    value_range: int
    mean_absolute_deviation: float
    variance: float
    standard_deviation: float
    coefficient_of_variation_percent: float | None


class FileSummary(BaseModel):
    metadata: ExplosivesMetadata
    signals_shape: tuple[int, int]
    background_shape: tuple[int]
    value_type: str = "int"
    signal_stats: ParsedSectionStats
    background_stats: ParsedSectionStats
    signals: dict[str, DescriptiveStatistics]
    background: DescriptiveStatistics


class AnalysisOutput(BaseModel):
    files_analyzed: int
    files_skipped: int
    signal_count: int
    files: list[FileSummary]


def describe_series(values: list[int]) -> DescriptiveStatistics:
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


def analyze_file(out: ParseOutput) -> FileSummary | None:
    if not out.success:
        return None

    data = out.data
    return FileSummary(
        metadata=data.metadata,
        signals_shape=(len(data.signals), len(data.signals[0])),
        background_shape=(len(data.background),),
        signal_stats=out.signal_stats,
        background_stats=out.background_stats,
        signals={f"S{index}": describe_series(signal) for index, signal in enumerate(data.signals)},
        background=describe_series(data.background),
    )


if __name__ == "__main__":
    def main():
        p_project = Path(__file__).parent.parent.parent
        p_data = p_project / "data_explosives"

        p_output = p_project / "output" / "analysis"
        p_analysis_out = p_output / "analysis_output.json"

        parsed_output: list[ParseOutput] = []
        for p in p_data.rglob("*.csv"):
            out = ExplosivesCsvParser.parse(p)
            if not out.success:
                print(f"Error in \"{p.relative_to(p_data)}\". Skipping")
                continue
            parsed_output.append(out)

        files: list[FileSummary] = []
        for out in parsed_output:
            summary = analyze_file(out)
            if summary is not None:
                files.append(summary)

        result = AnalysisOutput(
            files_analyzed=len(files),
            files_skipped=len(parsed_output) - len(files),
            signal_count=sum(len(file.signals) for file in files),
            files=files,
        )

        p_output.mkdir(parents=True, exist_ok=True)
        p_analysis_out.write_text(result.model_dump_json(indent=2))
        print(f"Saved to \"{p_analysis_out}\"")
    main()
