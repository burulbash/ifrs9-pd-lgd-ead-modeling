from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import REPORTS_DIR  # noqa: E402
from src.db import read_csv_table, read_postgres_table  # noqa: E402
from src.staging import (  # noqa: E402
    assign_ifrs9_stage,
    build_rating_migration_matrix,
    build_stage_by_rating,
    build_stage_distribution,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run IFRS 9 staging rules.")
    parser.add_argument("--source", choices=["postgres", "csv"], default="postgres")
    parser.add_argument("--csv-path", default=None)

    parser.add_argument("--db-host", default="localhost")
    parser.add_argument("--db-port", default="5432")
    parser.add_argument("--db-name", default="ifrs9_risk_db")
    parser.add_argument("--db-user", default="postgres")
    parser.add_argument("--table", default="mart.ifrs9_staging_sample")

    return parser.parse_args()


def load_dataset(args: argparse.Namespace) -> pd.DataFrame:
    if args.source == "csv":
        return read_csv_table(args.csv_path)

    return read_postgres_table(
        table_name=args.table,
        db_host=args.db_host,
        db_port=args.db_port,
        db_name=args.db_name,
        db_user=args.db_user,
    )


def main() -> None:
    args = parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    df = load_dataset(args)
    staged = assign_ifrs9_stage(df)

    stage_distribution = build_stage_distribution(staged)
    stage_by_rating = build_stage_by_rating(staged)
    migration_matrix = build_rating_migration_matrix(staged)

    staged.to_csv(REPORTS_DIR / "ifrs9_staged_portfolio.csv", index=False)
    stage_distribution.to_csv(REPORTS_DIR / "ifrs9_stage_distribution.csv", index=False)
    stage_by_rating.to_csv(REPORTS_DIR / "ifrs9_stage_by_rating.csv", index=False)
    migration_matrix.to_csv(REPORTS_DIR / "ifrs9_rating_migration_matrix.csv", index=False)

    print("IFRS 9 stage distribution")
    print(stage_distribution)
    print()
    print("Reports saved to:", REPORTS_DIR)


if __name__ == "__main__":
    main()
