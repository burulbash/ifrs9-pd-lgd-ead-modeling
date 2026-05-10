from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import MODELS_DIR, RANDOM_STATE, REPORTS_DIR  # noqa: E402
from src.db import read_csv_table, read_postgres_table  # noqa: E402
from src.metrics import compute_regression_metrics  # noqa: E402

try:
    from xgboost import XGBRegressor

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False


DATE_COL = "default_date"
TARGET_LGD = "realized_lgd"
WEIGHT_COL = "ead_at_default"

ID_AND_TARGET_COLUMNS = [
    "facility_id",
    "company_id",
    DATE_COL,
    TARGET_LGD,
]

LEAKAGE_COLUMNS = [
    "total_recovery_amount",
    "total_collection_cost",
    "net_recovery_amount",
    "recovery_events_count",
    "writeoff_flag",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train corporate LGD model.")
    parser.add_argument("--source", choices=["postgres", "csv"], default="postgres")
    parser.add_argument("--csv-path", default=None)

    parser.add_argument("--db-host", default="localhost")
    parser.add_argument("--db-port", default="5432")
    parser.add_argument("--db-name", default="ifrs9_risk_db")
    parser.add_argument("--db-user", default="postgres")
    parser.add_argument("--table", default="mart.lgd_modeling_sample")

    parser.add_argument("--include-xgboost", action="store_true")
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


def clip_lgd_values(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.clip(lower=0, upper=1)


def coerce_numeric_like_columns(
    df: pd.DataFrame,
    protected_columns: list[str],
    min_numeric_share: float = 0.80,
) -> pd.DataFrame:
    data = df.copy()
    protected = set(protected_columns)

    for column in data.columns:
        if column in protected:
            continue

        if not pd.api.types.is_object_dtype(data[column]):
            continue

        converted = pd.to_numeric(data[column], errors="coerce")
        non_missing_original = data[column].notna().sum()

        if non_missing_original == 0:
            continue

        numeric_share = converted.notna().sum() / non_missing_original

        if numeric_share >= min_numeric_share:
            data[column] = converted

    return data


def get_lgd_feature_columns(df: pd.DataFrame) -> list[str]:
    explicit_drop = set(ID_AND_TARGET_COLUMNS + LEAKAGE_COLUMNS)

    return [column for column in df.columns if column not in explicit_drop]


def infer_feature_types(
    df: pd.DataFrame,
    feature_columns: list[str],
) -> tuple[list[str], list[str]]:
    numeric_features = [
        column
        for column in feature_columns
        if pd.api.types.is_numeric_dtype(df[column])
    ]

    categorical_features = [
        column
        for column in feature_columns
        if column not in numeric_features
    ]

    return numeric_features, categorical_features


def make_lgd_time_split(
    df: pd.DataFrame,
    date_col: str = DATE_COL,
    target_col: str = TARGET_LGD,
    train_size: float = 0.70,
    valid_size: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data = df.copy()
    data[date_col] = pd.to_datetime(data[date_col], errors="coerce")
    data[target_col] = clip_lgd_values(data[target_col])
    data = data.dropna(subset=[date_col, target_col]).copy()
    data = data.sort_values(date_col).reset_index(drop=True)

    n_rows = len(data)
    train_end = int(n_rows * train_size)
    valid_end = int(n_rows * (train_size + valid_size))

    train_df = data.iloc[:train_end].copy()
    valid_df = data.iloc[train_end:valid_end].copy()
    oot_df = data.iloc[valid_end:].copy()

    summary = pd.DataFrame(
        [
            {
                "split": "train",
                "rows": len(train_df),
                "min_date": train_df[date_col].min(),
                "max_date": train_df[date_col].max(),
                "avg_lgd": train_df[target_col].mean(),
            },
            {
                "split": "valid",
                "rows": len(valid_df),
                "min_date": valid_df[date_col].min(),
                "max_date": valid_df[date_col].max(),
                "avg_lgd": valid_df[target_col].mean(),
            },
            {
                "split": "oot",
                "rows": len(oot_df),
                "min_date": oot_df[date_col].min(),
                "max_date": oot_df[date_col].max(),
                "avg_lgd": oot_df[target_col].mean(),
            },
        ]
    )

    return train_df, valid_df, oot_df, summary


def build_preprocessor(
    numeric_features: list[str],
    categorical_features: list[str],
    scale_numeric: bool,
) -> ColumnTransformer:
    numeric_steps = [("imputer", SimpleImputer(strategy="median"))]

    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))

    numeric_transformer = Pipeline(steps=numeric_steps)

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_transformer, numeric_features),
            ("categorical", categorical_transformer, categorical_features),
        ]
    )


def build_model_pipeline(
    estimator,
    numeric_features: list[str],
    categorical_features: list[str],
    scale_numeric: bool,
) -> Pipeline:
    return Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(
                    numeric_features=numeric_features,
                    categorical_features=categorical_features,
                    scale_numeric=scale_numeric,
                ),
            ),
            ("model", estimator),
        ]
    )


def get_models(
    numeric_features: list[str],
    categorical_features: list[str],
    include_xgboost: bool,
) -> dict[str, Pipeline]:
    models = {
        "dummy_mean": build_model_pipeline(
            estimator=DummyRegressor(strategy="mean"),
            numeric_features=numeric_features,
            categorical_features=categorical_features,
            scale_numeric=False,
        ),
        "ridge": build_model_pipeline(
            estimator=Ridge(alpha=1.0),
            numeric_features=numeric_features,
            categorical_features=categorical_features,
            scale_numeric=True,
        ),
        "random_forest": build_model_pipeline(
            estimator=RandomForestRegressor(
                n_estimators=200,
                max_depth=6,
                min_samples_leaf=3,
                n_jobs=-1,
                random_state=RANDOM_STATE,
            ),
            numeric_features=numeric_features,
            categorical_features=categorical_features,
            scale_numeric=False,
        ),
    }

    if include_xgboost and XGBOOST_AVAILABLE:
        models["xgboost"] = build_model_pipeline(
            estimator=XGBRegressor(
                n_estimators=200,
                max_depth=3,
                learning_rate=0.05,
                subsample=0.85,
                colsample_bytree=0.85,
                objective="reg:squarederror",
                random_state=RANDOM_STATE,
                n_jobs=-1,
            ),
            numeric_features=numeric_features,
            categorical_features=categorical_features,
            scale_numeric=False,
        )
    elif include_xgboost and not XGBOOST_AVAILABLE:
        print("XGBoost is not installed. Skipping xgboost model.")

    return models


def predict_lgd(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    predictions = model.predict(X)
    return np.clip(predictions, 0, 1)


def build_lgd_segment_report(
    df: pd.DataFrame,
    actual_col: str,
    pred_col: str,
    segment_col: str,
) -> pd.DataFrame:
    report = (
        df.groupby(segment_col, dropna=False)
        .agg(
            facilities=("facility_id", "size"),
            avg_actual_lgd=(actual_col, "mean"),
            avg_predicted_lgd=(pred_col, "mean"),
            avg_ead=(WEIGHT_COL, "mean"),
            total_ead=(WEIGHT_COL, "sum"),
        )
        .reset_index()
        .rename(columns={segment_col: "segment"})
    )

    report.insert(0, "segment_type", segment_col)
    report["prediction_error"] = report["avg_predicted_lgd"] - report["avg_actual_lgd"]

    return report.sort_values(["segment_type", "facilities"], ascending=[True, False])


def build_lgd_calibration_by_decile(
    df: pd.DataFrame,
    actual_col: str,
    pred_col: str,
    n_bins: int = 5,
) -> pd.DataFrame:
    data = df.copy()

    if data[pred_col].nunique(dropna=True) < 2:
        data["lgd_decile"] = 1
    else:
        data["lgd_decile"] = pd.qcut(
            data[pred_col].rank(method="first"),
            q=min(n_bins, len(data)),
            labels=False,
            duplicates="drop",
        ) + 1

    report = (
        data.groupby("lgd_decile", as_index=False)
        .agg(
            facilities=("facility_id", "size"),
            avg_actual_lgd=(actual_col, "mean"),
            avg_predicted_lgd=(pred_col, "mean"),
            total_ead=(WEIGHT_COL, "sum"),
        )
    )

    report["prediction_error"] = report["avg_predicted_lgd"] - report["avg_actual_lgd"]

    return report


def train_and_evaluate(df: pd.DataFrame, include_xgboost: bool) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    models_dir = MODELS_DIR / "lgd"
    models_dir.mkdir(parents=True, exist_ok=True)

    df[TARGET_LGD] = clip_lgd_values(df[TARGET_LGD])
    df = coerce_numeric_like_columns(df, protected_columns=ID_AND_TARGET_COLUMNS)

    feature_columns = get_lgd_feature_columns(df)
    numeric_features, categorical_features = infer_feature_types(df, feature_columns)

    print(f"Feature columns: {len(feature_columns)}")
    print(f"Numeric features: {len(numeric_features)}")
    print(f"Categorical features: {len(categorical_features)}")
    print()

    pd.DataFrame({"feature": feature_columns}).to_csv(
        REPORTS_DIR / "lgd_feature_columns.csv",
        index=False,
    )

    train_df, valid_df, oot_df, split_summary = make_lgd_time_split(df)
    split_summary.to_csv(REPORTS_DIR / "lgd_time_split_summary.csv", index=False)

    print("LGD time split summary")
    print(split_summary)
    print()

    X_train = train_df[feature_columns]
    y_train = train_df[TARGET_LGD].astype(float)
    train_weights = pd.to_numeric(train_df[WEIGHT_COL], errors="coerce").fillna(1).clip(lower=1)

    splits = {
        "train": train_df,
        "valid": valid_df,
        "oot": oot_df,
    }

    models = get_models(
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        include_xgboost=include_xgboost,
    )

    metrics_rows = []
    oot_predictions = oot_df[["facility_id", "company_id", DATE_COL, TARGET_LGD, WEIGHT_COL]].copy()

    for model_name, model in models.items():
        print(f"Training model: {model_name}")

        if model_name == "dummy_mean":
            model.fit(X_train, y_train)
        else:
            try:
                model.fit(X_train, y_train, model__sample_weight=train_weights)
            except TypeError:
                model.fit(X_train, y_train)

        joblib.dump(model, models_dir / f"{model_name}.joblib")

        for split_name, split_df in splits.items():
            X_split = split_df[feature_columns]
            y_split = split_df[TARGET_LGD].astype(float).to_numpy()
            weights = pd.to_numeric(split_df[WEIGHT_COL], errors="coerce").fillna(1).clip(lower=1).to_numpy()
            y_pred = predict_lgd(model, X_split)

            metrics = compute_regression_metrics(
                y_true=y_split,
                y_pred=y_pred,
                sample_weight=weights,
            )

            metrics_rows.append(
                {
                    "model": model_name,
                    "split": split_name,
                    "rows": len(split_df),
                    **metrics,
                }
            )

            if split_name == "oot":
                oot_predictions[f"lgd_{model_name}"] = y_pred

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df = metrics_df.sort_values(["split", "weighted_mae"], ascending=[True, True])
    metrics_df.to_csv(REPORTS_DIR / "lgd_model_metrics.csv", index=False)

    oot_metrics = metrics_df[metrics_df["split"] == "oot"].copy()
    best_row = oot_metrics.sort_values("weighted_mae", ascending=True).iloc[0]
    best_model_name = best_row["model"]
    best_lgd_column = f"lgd_{best_model_name}"

    segment_reports = []

    for segment_col in ["product_type", "collateral_type", "industry", "company_size", "origination_rating_grade"]:
        if segment_col in oot_df.columns:
            report_df = oot_predictions.merge(
                oot_df[["facility_id", segment_col]],
                on="facility_id",
                how="left",
            )
            segment_reports.append(
                build_lgd_segment_report(
                    report_df,
                    actual_col=TARGET_LGD,
                    pred_col=best_lgd_column,
                    segment_col=segment_col,
                )
            )

    lgd_by_segment = pd.concat(segment_reports, ignore_index=True) if segment_reports else pd.DataFrame()
    lgd_by_segment.to_csv(REPORTS_DIR / "lgd_by_segment.csv", index=False)

    calibration = build_lgd_calibration_by_decile(
        oot_predictions,
        actual_col=TARGET_LGD,
        pred_col=best_lgd_column,
        n_bins=5,
    )
    calibration.to_csv(REPORTS_DIR / "lgd_calibration_by_decile.csv", index=False)

    oot_predictions.to_csv(REPORTS_DIR / "lgd_oot_predictions.csv", index=False)
    pd.DataFrame([best_row]).to_csv(REPORTS_DIR / "lgd_best_model_summary.csv", index=False)

    print("LGD model metrics")
    print(metrics_df)
    print()
    print(f"Best OOT model: {best_model_name}")
    print()
    print("LGD calibration by decile")
    print(calibration)
    print()
    print(f"Reports saved to: {REPORTS_DIR}")
    print(f"LGD models saved to: {models_dir}")


def main() -> None:
    args = parse_args()

    df = load_dataset(args)
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df[TARGET_LGD] = clip_lgd_values(df[TARGET_LGD])
    df = df.dropna(subset=[DATE_COL, TARGET_LGD]).copy()

    if args.max_rows is not None:
        if args.max_rows <= 0:
            raise ValueError("--max-rows must be positive.")

        df = df.sort_values(DATE_COL).head(args.max_rows).copy()

    print("Basic checks")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")
    print(f"Average LGD: {df[TARGET_LGD].mean():.4f}")
    print(f"Default date range: {df[DATE_COL].min().date()} -> {df[DATE_COL].max().date()}")
    print()

    train_and_evaluate(
        df=df,
        include_xgboost=args.include_xgboost,
    )


if __name__ == "__main__":
    main()
