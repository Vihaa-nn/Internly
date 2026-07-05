from __future__ import annotations

import argparse
import csv
from pathlib import Path

from internly.db import crud
from internly.db.database import get_session, init_db
from internly.utils import parse_float


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest companywise DSA CSV files into SQLite.")
    parser.add_argument(
        "--source-dir",
        required=True,
        help="Local path to the leetcode-companywise-interview-questions repository.",
    )
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    init_db()
    count = 0
    with get_session() as session:
        for csv_path in source_dir.rglob("*.csv"):
            company = _company_from_path(source_dir, csv_path)
            for row in _read_rows(csv_path):
                title = _first_present(row, "Title", "title", "Problem", "problem", "Question", "question")
                if not title:
                    continue
                crud.upsert_dsa_question(
                    session,
                    company=company,
                    title=title,
                    difficulty=_first_present(row, "Difficulty", "difficulty"),
                    frequency=parse_float(_first_present(row, "Frequency", "frequency")),
                    acceptance=_first_present(row, "Acceptance", "acceptance", "Acceptance Rate"),
                    link=_first_present(row, "Link", "link", "URL", "url"),
                )
                count += 1
    print(f"Ingested or updated {count} DSA question rows.")


def _read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _company_from_path(source_dir: Path, csv_path: Path) -> str:
    relative = csv_path.relative_to(source_dir)
    if len(relative.parts) > 1:
        return relative.parts[0].replace("_", " ").replace("-", " ").title()
    return csv_path.stem.replace("_", " ").replace("-", " ").title()


def _first_present(row: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value and value.strip():
            return value.strip()
    return None


if __name__ == "__main__":
    main()

