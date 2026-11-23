from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from pprint import pprint
from typing import Final, Counter

from pydantic import BaseModel


class ParseOutput(BaseModel):
    success: bool
    data: ExplosivesFile
    signal_stats: ParsedSectionStats
    background_stats: ParsedSectionStats


class ExplosivesFile(BaseModel):
    signals_col_count: int
    signals: list[list[int]]
    background: list[int]

    metadata: ExplosivesMetadata


class ExplosivesMetadata(BaseModel):
    substance: str
    sample_type: SampleType
    concentration_ng: int | None
    source_path: Path


class ParsedSectionStats(BaseModel):
    num_cols: int = 0
    num_missing_fields: int = 0
    num_zero_fields: int = 0
    num_negative_fields: int = 0
    errors: list[str] = field(default_factory=list)


class SampleType(StrEnum):
    FINGER = "Палец"
    SOLUTION = "Растворы"


class ExplosivesCsvParser:
    section_lines_needed: Final[int] = 128

    class Section(StrEnum):
        Start = ""
        Signal = "Сигналы (S)"
        Background = "Фон"
        Calculated = "Спектры (SP);SP=(F-S)/F"

    @dataclass
    class SectionInterval:
        start: int
        end: int
        slice: list[str] = field(default_factory=list)

    @classmethod
    def parse(cls, p_file_csv: Path) -> ParseOutput:
        if not p_file_csv.exists() or not p_file_csv.is_file():
            raise FileNotFoundError

        lines = p_file_csv.read_text(encoding="utf-8").splitlines()
        intervals = cls._get_sections_intervals(lines)

        s_success, signals, s_stats = cls._parse_section(intervals[cls.Section.Signal])
        b_success, background, b_stats = cls._parse_section(intervals[cls.Section.Background], has_header=False)
        if len(background) != 1:
            b_success = False
            b_stats.errors.append("background must have 1 column")
        b_stats.num_cols = 1

        return ParseOutput(
            success=s_success and b_success,
            data=ExplosivesFile(
                signals_col_count=s_stats.num_cols,
                signals=signals,
                background=background[0],
                metadata=cls._get_explosives_meta(p_file_csv),
            ),
            signal_stats=s_stats,
            background_stats=b_stats,
        )

    @classmethod
    def _parse_section(
            cls,
            interval: SectionInterval,
            has_header: bool = True,
    ) -> tuple[bool, list[list[int]], ParsedSectionStats]:
        # errors: list[str] = []
        # signals_col_count: int = -1
        signals: list[list[int]] = []
        stats = ParsedSectionStats()

        for line_id, line in enumerate(interval.slice):
            raw_signals_line: list[str] = line.split(";")[:-1] if line.find(";") != -1 else [line]

            if has_header and line_id == 0:
                stats.num_cols = len(raw_signals_line)
                continue

            if line.isspace() or line == "" or all(el.isspace() or el == "" for el in raw_signals_line):
                continue

            try:
                signals_line: list[int] = []
                for field_id, raw_field in enumerate(raw_signals_line):
                    try:
                        field_int = int(raw_field)
                    except ValueError:
                        stats.errors.append(f"line={line_id + interval.start}: field={field_id}: is empty or incorrect.")
                        stats.num_missing_fields += 1
                        continue
                    if field_int == 0:
                        stats.num_zero_fields += 1
                    elif field_int < 0:
                        stats.num_negative_fields += 1
                    signals_line.append(field_int)
            except ValueError:
                stats.errors.append(f"line={line_id + interval.start}: signals must be an integer.")
                continue

            if has_header and len(signals_line) != stats.num_cols:
                stats.errors.append(f"line={line_id + interval.start}: signals line size is not equal to {stats.num_cols}.")

            signals.append(signals_line)

        if len(signals) != cls.section_lines_needed:
            stats.errors.append(f"signals lines != {cls.section_lines_needed}. Count: {len(signals)}")

        # transposition
        signals = [list(column) for column in zip(*signals, strict=True)]

        success: bool = len(stats.errors) == 0
        return success, signals, stats

    @classmethod
    def _get_sections_intervals(cls, lines: list[str]) -> dict[Section, SectionInterval]:
        sections: list[cls.Section] = [el for el in cls.Section]
        current_stage_index = 0
        stage_intervals: list[cls.SectionInterval] = [cls.SectionInterval(start=0, end=-1)]

        for line_id, line in enumerate(lines):
            current_stage = cls.Section(sections[current_stage_index])
            if current_stage == cls.Section.Calculated:
                break
            next_stage = sections[current_stage_index + 1]

            if line.find(next_stage) != -1 or line_id == len(lines):
                _interval = stage_intervals[current_stage_index]
                _interval.end = line_id
                _interval.slice = lines[_interval.start:_interval.end]

                current_stage_index += 1
                stage_intervals.append(cls.SectionInterval(start=line_id + 1, end=-1))
                continue

        return dict(zip(sections, stage_intervals))

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


def parse_explosives_csv(lines: list[str]) -> None:
    pprint(lines)


if __name__ == "__main__":
    def main():
        class SavedParseOutput(BaseModel):
            data: list[ParseOutput]

        class SavedStats(BaseModel):
            file: str
            success: bool
            signal_stats: ParsedSectionStats
            background_stats: ParsedSectionStats

        class StatsOutput(BaseModel):
            data: list[SavedStats]

        p_project = Path(__file__).parent.parent.parent
        p_data = p_project / "data_explosives"

        p_output = p_project / "output" / "parser"
        p_parsed_output = p_output / "parsed_output.json"
        p_stats_output = p_output / "stats.json"

        # p_csv_file = p_data / "Гексоген" / "Растворы" / "2500нг" / "1.csv"
        # p_csv_file = p_data / "Гексоген" / "Палец" / "Концентрация не задана" / "1.csv"

        success_count: int = 0
        files_count: int = 0
        output = SavedParseOutput(data=[])

        for p in p_data.rglob("*.csv"):
            out = ExplosivesCsvParser.parse(p)
            output.data.append(out)

            files_count += 1
            if out.success:
                success_count += 1

            print()
            print(f"{out.success = }")
            print(f"signal_stats: ", end="")
            pprint(out.signal_stats)
            print(f"background_stats: ", end="")
            pprint(out.background_stats)
            print(f"{out.data.metadata.substance = }")
            print(f"{out.data.metadata.sample_type = }")
            print(f"{out.data.metadata.concentration_ng = }")
            print(f"{out.data.metadata.source_path = }")
            print()
            print(f"{out.data.signals_col_count = }")
            # print(f"{out.data.signals = }")
            # print(f"{out.data.background = }")

        print()
        print("="*50)
        print(f"{files_count = }")
        print(f"{success_count = }")
        print(f"failed = {files_count - success_count}")
        print()
        print("signal num cols: ", Counter([
            el.signal_stats.num_cols
            for el in output.data
        ]))

        print("bg num cols: ", Counter([
            el.background_stats.num_cols
            for el in output.data
        ]))

        p_output.mkdir(parents=True, exist_ok=True)
        p_parsed_output.write_text(output.model_dump_json(indent=2))

        stats = StatsOutput(data=[
            SavedStats(
                file=el.data.metadata.source_path.relative_to(p_data).as_posix(),
                success=el.success,
                signal_stats=el.signal_stats,
                background_stats=el.background_stats
            )
            for el in output.data
        ])
        p_stats_output.write_text(stats.model_dump_json(indent=2))

    main()
