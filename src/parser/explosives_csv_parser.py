from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from pprint import pprint
from typing import Final


class SampleType(StrEnum):
    FINGER = "Палец"
    SOLUTION = "Растворы"


@dataclass
class ExplosivesFile:
    signals_col_count: int
    signals: list[list[int]]
    background: list[int]

    metadata: ExplosivesMetadata


@dataclass
class ExplosivesMetadata:
    substance: str
    sample_type: SampleType
    concentration_ng: int | None
    source_path: Path


class ExplosivesCsvParser:
    class Stage(StrEnum):
        Start = ""
        Signal = "Сигналы (S)"
        Background = "Фон"
        Calculated = "Спектры (SP);SP=(F-S)/F"

    @dataclass
    class StageInterval:
        start: int
        end: int
        slice: list[str] = field(default_factory=list)

    signal_lines_needed: Final[int] = 128
    bg_lines_needed: Final[int] = 128

    @classmethod
    def _get_explosives_meta(cls, p_file_csv: Path) -> ExplosivesMetadata:

        def get_substance(p_file: Path) -> str:
            return p_file.parent.parent.parent.name

        def get_sample_type(p_file: Path) -> SampleType:
            raw: str = p_file.parent.parent.name
            if raw not in SampleType:
                raise ValueError(f"Invalid sample type: {raw} in {p_file}")
            return SampleType(raw)

        def get_concentration(p_file: Path) -> int | None:
            raw_str: str = p_file.parent.name
            if raw_str == "Концентрация не задана":
                return None

            ng_index: int = raw_str.find("нг")
            if ng_index < 1:
                raise ValueError(f"Invalid concentration: {raw_str} in {p_file}")

            digits_raw = raw_str[:ng_index]
            if not digits_raw.isdigit():
                raise ValueError(f"Concentration must be digit: {raw_str} in {p_file}")

            return int(digits_raw)

        return ExplosivesMetadata(
            substance=get_substance(p_file_csv),
            sample_type=get_sample_type(p_file_csv),
            concentration_ng=get_concentration(p_file_csv),
            source_path=p_file_csv,
        )

    @classmethod
    def parse_explosives(cls, p_file_csv: Path) -> tuple[bool, ExplosivesFile, dict[str, list[str]]]:
        if not p_file_csv.exists() or not p_file_csv.is_file():
            raise FileNotFoundError

        lines = p_file_csv.read_text().splitlines()
        intervals = cls._get_stages_intervals(lines)

        s_success, signals_col_count, signals, s_errors = cls._parse_signals(intervals[cls.Stage.Signal])
        b_success, background, b_errors = cls._parse_background(intervals[cls.Stage.Background])

        success = s_success and b_success
        errors = {
            "signal": s_errors,
            "background": b_errors,
        }
        output = ExplosivesFile(
            signals_col_count=signals_col_count,
            signals=signals,
            background=background,
            metadata=cls._get_explosives_meta(p_file_csv),
        )

        return success, output, errors

    @classmethod
    def _parse_signals(cls, interval: StageInterval) -> tuple[bool, int, list[list[int]], list[str]]:
        errors: list[str] = []
        signals_col_count: int = -1
        signals: list[list[int]] = []

        for line_id, line in enumerate(interval.slice):
            raw_signals_line: list[str] = line.split(";")[:-1]

            if line_id == 0:
                signals_col_count = len(raw_signals_line)
                continue

            if line.isspace() or line == "":
                continue

            try:
                signals_line: list[int] = list(map(int, raw_signals_line))
            except ValueError:
                errors.append(f"line={line_id + interval.start}: signals must be an integer.")
                return False, signals_col_count, signals, errors

            if len(signals_line) != signals_col_count:
                errors.append(f"line={line_id + interval.start}: signals line size is not equal to {signals_col_count}")

            signals.append(signals_line)

        if len(signals) > cls.signal_lines_needed:
            errors.append(f"signals lines < {cls.signal_lines_needed}. Count: {len(signals)}")

        # transposition
        signals = [list(column) for column in zip(*signals, strict=True)]

        success: bool = len(errors) == 0
        return success, signals_col_count, signals, errors

    @classmethod
    def _parse_background(cls, interval: StageInterval) -> tuple[bool, list[int], list[str]]:
        bg: list[int] = []
        errors: list[str] = []

        for line_id, line in enumerate(interval.slice):
            if line.isspace() or line == "":
                continue
            if not line.isdigit():
                errors.append(f"line={line_id + interval.start}: background must be an integer.")
            bg.append(int(line))

        if len(bg) > cls.bg_lines_needed:
            errors.append(f"background lines < {cls.signal_lines_needed}. Count: {len(bg)}")

        success: bool = len(errors) == 0
        return success, bg, errors

    @classmethod
    def _get_stages_intervals(cls, lines: list[str]) -> dict[Stage, StageInterval]:
        stages: list[cls.Stage] = [el for el in cls.Stage]
        current_stage_index = 0
        stage_intervals: list[cls.StageInterval] = [cls.StageInterval(start=0, end=-1)]

        for line_id, line in enumerate(lines):
            current_stage = cls.Stage(stages[current_stage_index])
            if current_stage == cls.Stage.Calculated:
                break
            next_stage = stages[current_stage_index + 1]

            if line.find(next_stage) != -1 or line_id == len(lines):
                _interval = stage_intervals[current_stage_index]
                _interval.end = line_id
                _interval.slice = lines[_interval.start:_interval.end]

                current_stage_index += 1
                stage_intervals.append(cls.StageInterval(start=line_id+1, end=-1))
                continue

        return dict(zip(stages, stage_intervals))


def parse_explosives_csv(lines: list[str]) -> None:
    pprint(lines)


if __name__ == "__main__":
    def main():
        p_data = Path(__file__).parent.parent.parent / "data_explosives"
        p_csv_file = p_data / "Гексоген" / "Растворы" / "2500нг" / "1.csv"
        # p_csv_file = p_data / "Гексоген" / "Палец" / "Концентрация не задана" / "1.csv"

        success, out, errors = ExplosivesCsvParser.parse_explosives(p_csv_file)
        print()
        print(f"{success = }")
        print("errors: ", end="")
        pprint(errors)
        print(f"{out.metadata.substance = }")
        print(f"{out.metadata.sample_type = }")
        print(f"{out.metadata.concentration_ng = }")
        print(f"{out.metadata.source_path = }")
        print()
        print(f"{out.signals_col_count = }")
        print(f"{out.signals = }")
        print(f"{out.background = }")

    main()
