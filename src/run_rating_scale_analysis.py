from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import REPORTS_DIR  # noqa: E402
from src.rating_scale_analysis import (  # noqa: E402
    build_alternative_rating_backtesting,
    build_alternative_rating_mapping,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build alternative rating scale analysis.")
    parser.add_argument("--min-bucket-size", type=int, default=50)
    parser.add_argument("--input-report", default="pd_rating_grade_summary.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    input_path = REPORTS_DIR / args.input_report
    if not input_path.exists():
        raise FileNotFoundError(f"Rating summary not found: {input_path}")

    rating_summary = pd.read_csv(input_path)

    mapping = build_alternative_rating_mapping(
        rating_summary=rating_summary,
        min_bucket_size=args.min_bucket_size,
    )

    alternative_backtesting = build_alternative_rating_backtesting(
        rating_summary=rating_summary,
        mapping=mapping,
    )

    mapping_path = REPORTS_DIR / "rating_master_scale_alternative.csv"
    backtesting_path = REPORTS_DIR / "rating_backtesting_alternative.csv"

    mapping.to_csv(mapping_path, index=False)
    alternative_backtesting.to_csv(backtesting_path, index=False)

    print("Alternative rating mapping")
    print(mapping)
    print()
    print("Alternative rating backtesting")
    print(alternative_backtesting)
    print()
    print("Reports saved to:")
    print(mapping_path)
    print(backtesting_path)


if __name__ == "__main__":
    main()
