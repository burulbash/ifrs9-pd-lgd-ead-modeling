from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import REPORTS_DIR, SCENARIO_WEIGHTS  # noqa: E402
from src.db import read_csv_table, read_postgres_table  # noqa: E402
from src.ecl import (  # noqa: E402
    build_ecl_by_industry,
    build_ecl_by_rating,
    build_ecl_by_stage,
    build_ecl_portfolio_summary,
    calculate_ifrs9_ecl,
)
from src.staging import assign_ifrs9_stage  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run IFRS 9 ECL calculation.")
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

    ecl_df, scenario_summary = calculate_ifrs9_ecl(
        staged,
        scenario_weights=SCENARIO_WEIGHTS,
    )

    portfolio_summary = build_ecl_portfolio_summary(ecl_df)
    ecl_by_stage = build_ecl_by_stage(ecl_df)
    ecl_by_rating = build_ecl_by_rating(ecl_df)
    ecl_by_industry = build_ecl_by_industry(ecl_df)

    ecl_df.to_csv(REPORTS_DIR / "ifrs9_ecl_facility_level.csv", index=False)
    portfolio_summary.to_csv(REPORTS_DIR / "ifrs9_ecl_portfolio_summary.csv", index=False)
    ecl_by_stage.to_csv(REPORTS_DIR / "ifrs9_ecl_by_stage.csv", index=False)
    ecl_by_rating.to_csv(REPORTS_DIR / "ifrs9_ecl_by_rating.csv", index=False)
    ecl_by_industry.to_csv(REPORTS_DIR / "ifrs9_ecl_by_industry.csv", index=False)
    scenario_summary.to_csv(REPORTS_DIR / "ifrs9_ecl_by_scenario.csv", index=False)

    print("IFRS 9 ECL portfolio summary")
    print(portfolio_summary)
    print()

    print("ECL by stage")
    print(ecl_by_stage)
    print()

    print("ECL by scenario")
    print(scenario_summary)
    print()

    print("Reports saved to:", REPORTS_DIR)


if __name__ == "__main__":
    main()
