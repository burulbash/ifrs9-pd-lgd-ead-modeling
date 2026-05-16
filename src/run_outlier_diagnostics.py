from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import REPORTS_DIR  # noqa: E402
from src.db import read_csv_table, read_postgres_table  # noqa: E402
from src.outlier_diagnostics import (  # noqa: E402
    build_ead_ccf_outlier_report,
    build_lgd_outlier_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build LGD and EAD/CCF outlier diagnostics.")

    parser.add_argument("--source", choices=["postgres", "csv"], default="postgres")

    parser.add_argument("--lgd-csv-path", default="data/sample/lgd_modeling_sample.csv")
    parser.add_argument("--ead-csv-path", default="data/sample/ead_ccf_modeling_sample.csv")

    parser.add_argument("--db-host", default="localhost")
    parser.add_argument("--db-port", default="5432")
    parser.add_argument("--db-name", default="ifrs9_risk_db")
    parser.add_argument("--db-user", default="postgres")
    parser.add_argument("--lgd-table", default="mart.lgd_modeling_sample")
    parser.add_argument("--ead-table", default="mart.ead_ccf_modeling_sample")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.source == "csv":
        lgd_df = read_csv_table(args.lgd_csv_path)
        ead_df = read_csv_table(args.ead_csv_path)
    else:
        lgd_df = read_postgres_table(
            table_name=args.lgd_table,
            db_host=args.db_host,
            db_port=args.db_port,
            db_name=args.db_name,
            db_user=args.db_user,
        )
        ead_df = read_postgres_table(
            table_name=args.ead_table,
            db_host=args.db_host,
            db_port=args.db_port,
            db_name=args.db_name,
            db_user=args.db_user,
        )

    lgd_report = build_lgd_outlier_report(lgd_df)
    ead_report = build_ead_ccf_outlier_report(ead_df)

    lgd_output_path = REPORTS_DIR / "lgd_outlier_report.csv"
    ead_output_path = REPORTS_DIR / "ead_ccf_outlier_report.csv"

    lgd_report.to_csv(lgd_output_path, index=False)
    ead_report.to_csv(ead_output_path, index=False)

    print("LGD outlier diagnostics")
    print(lgd_report)
    print()
    print("EAD/CCF outlier diagnostics")
    print(ead_report)
    print()
    print("Reports saved to:")
    print(lgd_output_path)
    print(ead_output_path)


if __name__ == "__main__":
    main()
