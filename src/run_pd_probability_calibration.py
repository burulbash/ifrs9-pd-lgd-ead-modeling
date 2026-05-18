from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import DATE_COL, PLOTS_DIR, REPORTS_DIR, TARGET_DEFAULT_12M  # noqa: E402
from src.db import read_csv_table, read_postgres_table  # noqa: E402
from src.pd_probability_calibration import (  # noqa: E402
    build_calibrated_model_comparison,
    build_calibration_before_after_report,
)
from src.splitting import make_time_split  # noqa: E402
from src.train_pd_model import (  # noqa: E402
    ID_AND_TARGET_COLUMNS,
    build_model_pipeline,
    coerce_numeric_like_columns,
    get_pd_feature_columns,
    infer_feature_types,
)
from sklearn.linear_model import LogisticRegression  # noqa: E402
from src.config import RANDOM_STATE  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PD probability calibration analysis.")

    parser.add_argument("--source", choices=["postgres", "csv"], default="postgres")
    parser.add_argument("--csv-path", default=None)

    parser.add_argument("--db-host", default="localhost")
    parser.add_argument("--db-port", default="5432")
    parser.add_argument("--db-name", default="ifrs9_risk_db")
    parser.add_argument("--db-user", default="postgres")
    parser.add_argument("--table", default="mart.pd_modeling_sample")

    parser.add_argument("--max-rows", type=int, default=None)

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


def save_calibration_plot(report: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(9, 5))

    observed = (
        report.groupby("pd_decile", as_index=False)
        .agg(observed_default_rate=("observed_default_rate", "mean"))
        .sort_values("pd_decile")
    )

    ax.plot(
        observed["pd_decile"],
        observed["observed_default_rate"],
        marker="o",
        label="observed default rate",
    )

    for model_name, model_df in report.groupby("model"):
        model_df = model_df.sort_values("pd_decile")
        ax.plot(
            model_df["pd_decile"],
            model_df["avg_predicted_pd"],
            marker="o",
            label=f"{model_name} avg predicted PD",
        )

    ax.set_title("PD calibration before and after calibration")
    ax.set_xlabel("PD decile")
    ax.set_ylabel("Default rate / predicted PD")
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> None:
    args = parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    df = load_dataset(args)
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df[TARGET_DEFAULT_12M] = pd.to_numeric(df[TARGET_DEFAULT_12M], errors="coerce")
    df = df.dropna(subset=[DATE_COL, TARGET_DEFAULT_12M]).copy()

    if args.max_rows is not None:
        df = df.sort_values(DATE_COL).head(args.max_rows).copy()

    feature_columns, suspicious_columns = get_pd_feature_columns(df)

    df = coerce_numeric_like_columns(
        df,
        protected_columns=ID_AND_TARGET_COLUMNS,
    )

    numeric_features, categorical_features = infer_feature_types(df, feature_columns)

    train_df, valid_df, oot_df, _ = make_time_split(df)

    X_train = train_df[feature_columns]
    y_train = train_df[TARGET_DEFAULT_12M].astype(int)

    X_valid = valid_df[feature_columns]
    y_valid = valid_df[TARGET_DEFAULT_12M].astype(int)

    X_oot = oot_df[feature_columns]
    y_oot = oot_df[TARGET_DEFAULT_12M].astype(int)

    base_model = build_model_pipeline(
        estimator=LogisticRegression(
            max_iter=2000,
            solver="lbfgs",
            random_state=RANDOM_STATE,
        ),
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        scale_numeric=True,
    )

    metrics, prediction_map = build_calibrated_model_comparison(
        base_model=base_model,
        X_train=X_train,
        y_train=y_train,
        X_valid=X_valid,
        y_valid=y_valid,
        X_oot=X_oot,
        y_oot=y_oot,
    )

    calibration_report = build_calibration_before_after_report(
        y_true=y_oot,
        prediction_map=prediction_map,
    )

    metrics_path = REPORTS_DIR / "pd_model_metrics_calibrated.csv"
    calibration_path = REPORTS_DIR / "pd_calibration_before_after.csv"
    plot_path = PLOTS_DIR / "pd_calibration_before_after.png"

    metrics.to_csv(metrics_path, index=False)
    calibration_report.to_csv(calibration_path, index=False)
    save_calibration_plot(calibration_report, plot_path)

    print("PD calibrated model metrics")
    print(metrics)
    print()
    print("Calibration before/after report")
    print(calibration_report.head(20))
    print()
    print("Reports saved to:")
    print(metrics_path)
    print(calibration_path)
    print(plot_path)


if __name__ == "__main__":
    main()
