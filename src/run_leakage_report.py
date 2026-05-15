from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import REPORTS_DIR  # noqa: E402
from src.db import read_csv_table, read_postgres_table  # noqa: E402
from src.leakage import build_leakage_exclusion_report  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build PD leakage exclusion report.")

    parser.add_argument("--source", choices=["postgres", "csv"], default="csv")
    parser.add_argument("--csv-path", default="data/sample/pd_modeling_sample.csv")

    parser.add_argument("--db-host", default="localhost")
    parser.add_argument("--db-port", default="5432")
    parser.add_argument("--db-name", default="ifrs9_risk_db")
    parser.add_argument("--db-user", default="postgres")
    parser.add_argument("--table", default="mart.pd_modeling_sample")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.source == "csv":
        df = read_csv_table(args.csv_path)
    else:
        df = read_postgres_table(
            table_name=args.table,
            db_host=args.db_host,
            db_port=args.db_port,
            db_name=args.db_name,
            db_user=args.db_user,
        )

    report = build_leakage_exclusion_report(df)
    output_path = REPORTS_DIR / "leakage_exclusion_report.csv"
    report.to_csv(output_path, index=False)

    print("Leakage exclusion report")
    print(report)
    print()
    print("Report saved to:", output_path)


if __name__ == "__main__":
    main()
