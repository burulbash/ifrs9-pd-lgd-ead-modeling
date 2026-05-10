from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import DATE_COL, MODELS_DIR, RANDOM_STATE, REPORTS_DIR, TARGET_DEFAULT_12M  # noqa: E402
from src.db import read_csv_table, read_postgres_table  # noqa: E402
from src.metrics import compute_binary_metrics  # noqa: E402
from src.splitting import make_time_split  # noqa: E402

try:
    from xgboost import XGBClassifier

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False


ID_AND_TARGET_COLUMNS = [
    "facility_id",
    "company_id",
    DATE_COL,
    TARGET_DEFAULT_12M,
]

LEAKAGE_COLUMNS = [
    "default_date",
    "default_type",
    "dpd_at_default",
    "ead_at_default",
    "writeoff_flag",
    "max_dpd_observed",
    "max_dpd_12m",
    "target_default_12m",
    "realized_lgd",
    "realized_ccf",
    "total_recovery_amount",
    "total_collection_cost",
    "recovery_events_count",
]

SAFETY_EXCLUDE_TOKENS = [
    "target",
    "default_date",
    "ead_at_default",
    "realized_lgd",
    "realized_ccf",
    "recovery",
    "dpd",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train corporate PD model.")
    parser.add_argument("--source", choices=["postgres", "csv"], default="postgres")
    parser.add_argument("--csv-path", default=None)

    parser.add_argument("--db-host", default="localhost")
    parser.add_argument("--db-port", default="5432")
    parser.add_argument("--db-name", default="ifrs9_risk_db")
    parser.add_argument("--db-user", default="postgres")
    parser.add_argument("--table", default="mart.pd_modeling_sample")

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


def coerce_numeric_like_columns(
    df: pd.DataFrame,
    protected_columns: list[str],
    min_numeric_share: float = 0.80,
) -> pd.DataFrame:
    """Convert object columns that are mostly numeric to numeric dtype."""

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


def get_pd_feature_columns(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    explicit_drop = set(ID_AND_TARGET_COLUMNS + LEAKAGE_COLUMNS)

    candidates = [column for column in df.columns if column not in explicit_drop]

    suspicious_columns = [
        column
        for column in candidates
        if any(token in column.lower() for token in SAFETY_EXCLUDE_TOKENS)
    ]

    features = [column for column in candidates if column not in suspicious_columns]

    return features, suspicious_columns


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
        "dummy_prior": build_model_pipeline(
            estimator=DummyClassifier(strategy="prior"),
            numeric_features=numeric_features,
            categorical_features=categorical_features,
            scale_numeric=False,
        ),
        "logistic_regression": build_model_pipeline(
            estimator=LogisticRegression(
                max_iter=2000,
                solver="lbfgs",
                random_state=RANDOM_STATE,
            ),
            numeric_features=numeric_features,
            categorical_features=categorical_features,
            scale_numeric=True,
        ),
        "random_forest": build_model_pipeline(
            estimator=RandomForestClassifier(
                n_estimators=200,
                max_depth=7,
                min_samples_leaf=25,
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
            estimator=XGBClassifier(
                n_estimators=200,
                max_depth=3,
                learning_rate=0.05,
                subsample=0.85,
                colsample_bytree=0.85,
                objective="binary:logistic",
                eval_metric="logloss",
                tree_method="hist",
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


def predict_positive_proba(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    probabilities = model.predict_proba(X)

    if probabilities.shape[1] == 1:
        return np.full(len(X), float(model.named_steps["model"].class_prior_[0]))

    return probabilities[:, 1]


def assign_pd_rating_grade(pd_value: float) -> str:
    if pd_value < 0.005:
        return "A"
    if pd_value < 0.015:
        return "B"
    if pd_value < 0.035:
        return "C"
    if pd_value < 0.075:
        return "D"
    if pd_value < 0.150:
        return "E"
    return "F"


def build_rating_summary(
    predictions: pd.DataFrame,
    pd_column: str,
    target_column: str = TARGET_DEFAULT_12M,
) -> pd.DataFrame:
    data = predictions.copy()
    data["rating_grade"] = data[pd_column].apply(assign_pd_rating_grade)

    grade_order = pd.DataFrame(
        {
            "rating_grade": ["A", "B", "C", "D", "E", "F"],
            "grade_order": [1, 2, 3, 4, 5, 6],
        }
    )

    summary = (
        data.groupby("rating_grade", as_index=False)
        .agg(
            facilities=("facility_id", "size"),
            observed_defaults=(target_column, "sum"),
            observed_default_rate=(target_column, "mean"),
            avg_predicted_pd=(pd_column, "mean"),
            min_predicted_pd=(pd_column, "min"),
            max_predicted_pd=(pd_column, "max"),
        )
    )

    summary = grade_order.merge(summary, on="rating_grade", how="left")
    summary["facilities"] = summary["facilities"].fillna(0).astype(int)
    summary["observed_defaults"] = summary["observed_defaults"].fillna(0).astype(int)

    return summary.sort_values("grade_order").drop(columns=["grade_order"])


def train_and_evaluate(
    df: pd.DataFrame,
    include_xgboost: bool,
) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    models_dir = MODELS_DIR / "pd"
    models_dir.mkdir(parents=True, exist_ok=True)

    feature_columns, suspicious_columns = get_pd_feature_columns(df)
    df = coerce_numeric_like_columns(df, protected_columns=ID_AND_TARGET_COLUMNS)

    numeric_features, categorical_features = infer_feature_types(df, feature_columns)

    print(f"Feature columns: {len(feature_columns)}")
    print(f"Excluded suspicious columns: {len(suspicious_columns)}")
    print(f"Numeric features: {len(numeric_features)}")
    print(f"Categorical features: {len(categorical_features)}")
    print()

    pd.DataFrame({"feature": feature_columns}).to_csv(
        REPORTS_DIR / "pd_feature_columns.csv",
        index=False,
    )
    pd.DataFrame({"excluded_suspicious_column": suspicious_columns}).to_csv(
        REPORTS_DIR / "pd_excluded_suspicious_columns.csv",
        index=False,
    )

    train_df, valid_df, oot_df, split_summary = make_time_split(df)
    split_summary.to_csv(REPORTS_DIR / "pd_time_split_summary.csv", index=False)

    print("Time split summary")
    print(split_summary)
    print()

    X_train = train_df[feature_columns]
    y_train = train_df[TARGET_DEFAULT_12M].astype(int)

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
    oot_predictions = oot_df[["facility_id", "company_id", DATE_COL, TARGET_DEFAULT_12M]].copy()

    for model_name, model in models.items():
        print(f"Training model: {model_name}")

        model.fit(X_train, y_train)

        joblib.dump(model, models_dir / f"{model_name}.joblib")

        for split_name, split_df in splits.items():
            X_split = split_df[feature_columns]
            y_split = split_df[TARGET_DEFAULT_12M].astype(int).to_numpy()
            y_score = predict_positive_proba(model, X_split)

            metrics = compute_binary_metrics(y_true=y_split, y_score=y_score)
            metrics_rows.append(
                {
                    "model": model_name,
                    "split": split_name,
                    "rows": len(split_df),
                    "default_rate": float(np.mean(y_split)),
                    **metrics,
                }
            )

            if split_name == "oot":
                oot_predictions[f"pd_{model_name}"] = y_score

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df = metrics_df.sort_values(["split", "roc_auc"], ascending=[True, False])
    metrics_df.to_csv(REPORTS_DIR / "pd_model_metrics.csv", index=False)

    oot_metrics = metrics_df[metrics_df["split"] == "oot"].copy()
    best_row = oot_metrics.sort_values("roc_auc", ascending=False).iloc[0]
    best_model_name = best_row["model"]
    best_pd_column = f"pd_{best_model_name}"

    rating_summary = build_rating_summary(
        predictions=oot_predictions,
        pd_column=best_pd_column,
    )

    rating_summary.to_csv(REPORTS_DIR / "pd_rating_grade_summary.csv", index=False)
    oot_predictions.to_csv(REPORTS_DIR / "pd_oot_predictions.csv", index=False)

    pd.DataFrame([best_row]).to_csv(REPORTS_DIR / "pd_best_model_summary.csv", index=False)

    print("PD model metrics")
    print(metrics_df)
    print()
    print(f"Best OOT model: {best_model_name}")
    print()
    print("Rating grade summary")
    print(rating_summary)
    print()
    print(f"Reports saved to: {REPORTS_DIR}")
    print(f"PD models saved to: {models_dir}")


def main() -> None:
    args = parse_args()

    df = load_dataset(args)
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df[TARGET_DEFAULT_12M] = pd.to_numeric(df[TARGET_DEFAULT_12M], errors="coerce")
    df = df.dropna(subset=[DATE_COL, TARGET_DEFAULT_12M]).copy()

    if args.max_rows is not None:
        if args.max_rows <= 0:
            raise ValueError("--max-rows must be positive.")

        df = df.sort_values(DATE_COL).head(args.max_rows).copy()

    print("Basic checks")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")
    print(f"Default rate: {df[TARGET_DEFAULT_12M].mean():.4f}")
    print(f"Date range: {df[DATE_COL].min().date()} -> {df[DATE_COL].max().date()}")
    print()

    train_and_evaluate(
        df=df,
        include_xgboost=args.include_xgboost,
    )


if __name__ == "__main__":
    main()
