from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import DATE_COL, REPORTS_DIR, TARGET_DEFAULT_12M  # noqa: E402
from src.db import read_postgres_table  # noqa: E402
from src.splitting import make_time_split  # noqa: E402
from src.validation import (  # noqa: E402
    build_ecl_validation_summary,
    build_pd_backtesting_by_rating,
    build_rating_binomial_backtesting,
    build_pd_calibration_by_decile,
    build_psi_report,
    build_stage_validation_summary,
    build_validation_summary,
    check_rating_monotonicity,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run model validation and monitoring reports.")

    parser.add_argument("--db-host", default="localhost")
    parser.add_argument("--db-port", default="5432")
    parser.add_argument("--db-name", default="ifrs9_risk_db")
    parser.add_argument("--db-user", default="postgres")
    parser.add_argument("--pd-table", default="mart.pd_modeling_sample")

    parser.add_argument("--pd-predictions-path", default="outputs/reports/pd_oot_predictions.csv")
    parser.add_argument("--pd-best-model-path", default="outputs/reports/pd_best_model_summary.csv")
    parser.add_argument("--staged-portfolio-path", default="outputs/reports/ifrs9_staged_portfolio.csv")
    parser.add_argument("--ecl-portfolio-path", default="outputs/reports/ifrs9_ecl_facility_level.csv")

    parser.add_argument("--psi-top-n", type=int, default=20)

    return parser.parse_args()


def choose_best_pd_column(predictions: pd.DataFrame, best_model_path: str) -> str:
    path = Path(best_model_path)

    if path.exists():
        best_model = pd.read_csv(path)["model"].iloc[0]
        candidate = f"pd_{best_model}"

        if candidate in predictions.columns:
            return candidate

    pd_columns = [
        column
        for column in predictions.columns
        if column.startswith("pd_") and column not in {"pd_dummy_prior"}
    ]

    if pd_columns:
        return pd_columns[0]

    raise ValueError("No PD prediction columns found.")


def get_numeric_psi_features(df: pd.DataFrame) -> list[str]:
    excluded = {
        "facility_id",
        "company_id",
        DATE_COL,
        TARGET_DEFAULT_12M,
    }

    return [
        column
        for column in df.columns
        if column not in excluded and pd.api.types.is_numeric_dtype(df[column])
    ]


def main() -> None:
    args = parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    predictions = pd.read_csv(args.pd_predictions_path)
    best_pd_column = choose_best_pd_column(predictions, args.pd_best_model_path)

    pd_backtesting = build_pd_backtesting_by_rating(
        predictions=predictions,
        pd_column=best_pd_column,
        target_column=TARGET_DEFAULT_12M,
    )

    rating_binomial_backtesting = build_rating_binomial_backtesting(pd_backtesting)

    monotonicity_summary, monotonicity_violations = check_rating_monotonicity(pd_backtesting)

    pd_calibration = build_pd_calibration_by_decile(
        predictions=predictions,
        pd_column=best_pd_column,
        target_column=TARGET_DEFAULT_12M,
        n_bins=10,
    )

    pd_sample = read_postgres_table(
        table_name=args.pd_table,
        db_host=args.db_host,
        db_port=args.db_port,
        db_name=args.db_name,
        db_user=args.db_user,
    )

    train_df, _, oot_df, _ = make_time_split(pd_sample)

    psi_features = get_numeric_psi_features(train_df)
    psi_summary, psi_details = build_psi_report(
        expected_df=train_df,
        actual_df=oot_df,
        features=psi_features,
        bins=10,
    )

    if args.psi_top_n > 0:
        top_features = psi_summary.head(args.psi_top_n)["feature"].tolist()
        psi_details = psi_details[psi_details["feature"].isin(top_features)].copy()

    staged_portfolio = pd.read_csv(args.staged_portfolio_path)
    stage_summary = build_stage_validation_summary(staged_portfolio)

    ecl_portfolio = pd.read_csv(args.ecl_portfolio_path)
    ecl_summary = build_ecl_validation_summary(ecl_portfolio)

    validation_summary = build_validation_summary(
        pd_backtesting=pd_backtesting,
        monotonicity_summary=monotonicity_summary,
        psi_summary=psi_summary,
        stage_summary=stage_summary,
        ecl_summary=ecl_summary,
    )

    pd_backtesting.to_csv(REPORTS_DIR / "validation_pd_backtesting_by_rating.csv", index=False)
    rating_binomial_backtesting.to_csv(REPORTS_DIR / "validation_rating_binomial_backtesting.csv", index=False)
    pd_calibration.to_csv(REPORTS_DIR / "validation_pd_calibration_by_decile.csv", index=False)
    monotonicity_summary.to_csv(REPORTS_DIR / "validation_rating_monotonicity_summary.csv", index=False)
    monotonicity_violations.to_csv(REPORTS_DIR / "validation_rating_monotonicity_violations.csv", index=False)
    psi_summary.to_csv(REPORTS_DIR / "validation_psi_summary.csv", index=False)
    psi_details.to_csv(REPORTS_DIR / "validation_psi_details.csv", index=False)
    stage_summary.to_csv(REPORTS_DIR / "validation_stage_summary.csv", index=False)
    ecl_summary.to_csv(REPORTS_DIR / "validation_ecl_summary.csv", index=False)
    validation_summary.to_csv(REPORTS_DIR / "validation_summary.csv", index=False)

    print("Validation summary")
    print(validation_summary)
    print()

    print("PD backtesting by rating")
    print(pd_backtesting)
    print()

    print("Rating monotonicity")
    print(monotonicity_summary)
    print()

    print("Top PSI features")
    print(psi_summary.head(10))
    print()

    print("Reports saved to:", REPORTS_DIR)


if __name__ == "__main__":
    main()
