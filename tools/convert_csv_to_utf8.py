from pathlib import Path
from tempfile import TemporaryDirectory


def convert_csv_to_utf8(source: Path, dest: Path):
    csv_files = sorted(source.rglob("*.csv"))
    if not csv_files:
        raise Exception(f"No CSV files found in {source}")
    if dest.exists():
        raise Exception(f"Destination already exists: {dest}")

    try:
        with TemporaryDirectory(dir=dest.parent) as temporary_dir:
            staging = Path(temporary_dir)
            for csv_file in csv_files:
                target = staging / csv_file.relative_to(source)
                contents = csv_file.read_bytes().decode("cp1251")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(contents.encode("utf-8"))
                print(f"{source.name / csv_file.relative_to(source)} -> {dest.name / target.relative_to(staging)}")

            staging.rename(dest)
    except (OSError, UnicodeError) as error:
        raise Exception(f"Conversion failed: {error}")

    print(f"Converted {len(csv_files)} CSV files to UTF-8 in {dest}")


def main() -> None:
    p_project = Path(__file__).parent.parent

    p_data = p_project / "data"
    p_destination = p_project / "data_explosives"

    convert_csv_to_utf8(p_data, p_destination)


if __name__ == "__main__":
    main()
