from collections import defaultdict
from collections.abc import Sequence
from csv import writer
from dataclasses import dataclass
from pathlib import Path
from random import Random
from typing import DefaultDict

from analysis.preprocessing import get_spectrum
from parser.explosives_csv_parser import ExplosivesCsvParser, ExplosivesMetadata


SAMPLE_COUNT = ExplosivesCsvParser.section_lines_needed


@dataclass
class SourceSpectrum:
    metadata: ExplosivesMetadata
    spectrum: list[list[float]]


def select_test_paths(groups: Sequence[SourceSpectrum], test_fraction: float, rng: Random) -> set[Path]:
    if len(groups) < 2:
        substance = groups[0].metadata.substance
        raise ValueError(f"At least two CSV files are required to split class {substance}")

    total = sum(len(group.spectrum) for group in groups)
    target = total * test_fraction
    paths_by_count: dict[int, tuple[Path, ...]] = {0: ()}

    for group in rng.sample(list(groups), len(groups)):
        for count, paths in list(paths_by_count.items()):
            new_count = count + len(group.spectrum)
            if new_count < total and new_count not in paths_by_count:
                paths_by_count[new_count] = (*paths, group.metadata.source_path)

    best_count = min((count for count in paths_by_count if count), key=lambda count: abs(count - target))
    return set(paths_by_count[best_count])


def write_split(path: Path, groups: Sequence[SourceSpectrum], source_dir: Path) -> None:
    features = [f"x_{index:03d}" for index in range(1, SAMPLE_COUNT + 1)]
    with path.open("w", encoding="utf-8", newline="") as output:
        csv = writer(output)
        csv.writerow([*features, "substance", "sample_type", "concentration_ng", "source_path", "signal_index"])

        for group in groups:
            metadata = group.metadata
            relative_path = metadata.source_path.relative_to(source_dir).as_posix()
            for index, spectrum in enumerate(group.spectrum):
                csv.writerow([
                    *spectrum,
                    metadata.substance,
                    metadata.sample_type.value,
                    metadata.concentration_ng,
                    relative_path,
                    index,
                ])


def build_dataset(source_dir: Path, output_dir: Path, *, test_fraction: float, seed: int) -> None:
    if not 0 < test_fraction < 1:
        raise ValueError("The test fraction must be > 0 and < 1.")

    groups_by_substance: DefaultDict[str, list[SourceSpectrum]] = defaultdict(list)
    skipped: int = 0
    for path in sorted(source_dir.rglob("*.csv")):
        try:
            parsed = ExplosivesCsvParser.parse(path)
            if not parsed.success:
                errors = parsed.signal_stats.errors + parsed.background_stats.errors
                raise ValueError(f"The CSV failed parser validation: {repr(errors)[:200]}")

            data = parsed.data
            spectrum = [get_spectrum(signal, data.background) for signal in data.signals]

            if not spectrum or any(len(spectrum) != SAMPLE_COUNT for spectrum in spectrum):
                raise ValueError(f"Every spectrum must contain {SAMPLE_COUNT} samples")
        except (ValueError, KeyError, IndexError) as error:
            print(f"Skipped {path.relative_to(source_dir)}: {error}")
            skipped += 1
            continue

        groups_by_substance[data.metadata.substance].append(SourceSpectrum(data.metadata, spectrum))

    if not groups_by_substance:
        raise ValueError(f"No usable CSV files found in {source_dir}")

    rng = Random(seed)
    train: list[SourceSpectrum] = []
    test: list[SourceSpectrum] = []
    for groups in groups_by_substance.values():
        groups_by_sample_type: DefaultDict[str, list[SourceSpectrum]] = defaultdict(list)
        for group in groups:
            groups_by_sample_type[group.metadata.sample_type.value].append(group)

        split_groups = [sample_groups for sample_groups in groups_by_sample_type.values() if len(sample_groups) > 1]
        test_paths: set[Path] = set()
        for sample_groups in split_groups or [groups]:
            test_paths.update(select_test_paths(sample_groups, test_fraction, rng))

        for group in groups:
            split = test if group.metadata.source_path in test_paths else train
            split.append(group)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_split(output_dir / "train.csv", train, source_dir)
    write_split(output_dir / "test.csv", test, source_dir)

    train_count = sum(len(group.spectrum) for group in train)
    test_count = sum(len(group.spectrum) for group in test)
    total = train_count + test_count
    print(f"train: {train_count} ({train_count / total:.1%}), test: {test_count} ({test_count / total:.1%})")
    print(f"CSV files processed: {len(train) + len(test)}. Skipped: {skipped}.")
    print(f"Dataset saved to {output_dir}")


def main() -> None:
    project_dir = Path(__file__).resolve().parent.parent
    source_dir = project_dir / "data_explosives"
    output_dir = project_dir / "output" / "dataset"
    build_dataset(source_dir, output_dir, test_fraction=0.2, seed=42)


if __name__ == "__main__":
    main()
