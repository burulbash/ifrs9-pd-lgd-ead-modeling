from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import REPORTS_DIR  # noqa: E402
from src.db import read_csv_table, read_postgres_table  # noqa: E402
from src.staging import assign_ifrs9_stage  # noqa: E402
from src.stress_scenarios import calculate_stress_scenario_ecl  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run IFRS 9 ECL stress scenarios.")
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

    stress_df, scenario_summary, by_stage, by_industry = calculate_stress_scenario_ecl(staged)

    stress_df.to_csv(REPORTS_DIR / "stress_scenario_facility_level.csv", index=False)
    scenario_summary.to_csv(REPORTS_DIR / "stress_scenario_summary.csv", index=False)
    by_stage.to_csv(REPORTS_DIR / "stress_scenario_by_stage.csv", index=False)
    by_industry.to_csv(REPORTS_DIR / "stress_scenario_by_industry.csv", index=False)

    print("Stress scenario summary")
    print(scenario_summary)
    print()

    print("Stress scenario by stage")
    print(by_stage)
    print()

    print("Reports saved to:", REPORTS_DIR)


if __name__ == "__main__":
    main()
