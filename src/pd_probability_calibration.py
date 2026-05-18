from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.base import clone

from src.config import TARGET_DEFAULT_12M
from src.metrics import compute_binary_metrics


def fit_prefit_calibrator(
    fitted_model,
    X_valid: pd.DataFrame,
    y_valid: pd.Series,
    method: str,
):
    """Calibrate an already fitted estimator on a validation sample.

    Newer scikit-learn versions replaced cv="prefit" with FrozenEstimator.
    The fallback keeps the code compatible with older versions.
    """

    try:
        from sklearn.frozen import FrozenEstimator

        calibrator = CalibratedClassifierCV(
            estimator=FrozenEstimator(fitted_model),
            method=method,
        )
    except ImportError:
        calibrator = CalibratedClassifierCV(
            estimator=fitted_model,
            method=method,
            cv="prefit",
        )

    calibrator.fit(X_valid, y_valid)
    return calibrator


def predict_positive_proba(model, X: pd.DataFrame) -> np.ndarray:
    probabilities = model.predict_proba(X)
    if probabilities.shape[1] == 1:
        return np.zeros(len(X), dtype=float)
    return probabilities[:, 1]


def build_calibrated_model_comparison(
    base_model,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_valid: pd.DataFrame,
    y_valid: pd.Series,
    X_oot: pd.DataFrame,
    y_oot: pd.Series,
    methods: list[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    if methods is None:
        methods = ["sigmoid", "isotonic"]

    fitted_base = clone(base_model)
    fitted_base.fit(X_train, y_train)

    prediction_map: dict[str, np.ndarray] = {
        "raw": predict_positive_proba(fitted_base, X_oot)
    }

    metrics_rows = []

    raw_metrics = compute_binary_metrics(y_true=y_oot.to_numpy(), y_score=prediction_map["raw"])
    metrics_rows.append(
        {
            "model": "logistic_regression_raw",
            "calibration_method": "none",
            "split": "oot",
            "rows": len(y_oot),
            **raw_metrics,
        }
    )

    for method in methods:
        try:
            calibrator = fit_prefit_calibrator(
                fitted_model=fitted_base,
                X_valid=X_valid,
                y_valid=y_valid,
                method=method,
            )
            scores = predict_positive_proba(calibrator, X_oot)
        except Exception as exc:
            metrics_rows.append(
                {
                    "model": f"logistic_regression_{method}_calibrated",
                    "calibration_method": method,
                    "split": "oot",
                    "rows": len(y_oot),
                    "roc_auc": np.nan,
                    "gini": np.nan,
                    "ks": np.nan,
                    "average_precision": np.nan,
                    "brier_score": np.nan,
                    "mean_predicted_pd": np.nan,
                    "observed_default_rate": float(np.mean(y_oot)),
                    "error": str(exc),
                }
            )
            continue

        prediction_map[method] = scores

        metrics = compute_binary_metrics(y_true=y_oot.to_numpy(), y_score=scores)
        metrics_rows.append(
            {
                "model": f"logistic_regression_{method}_calibrated",
                "calibration_method": method,
                "split": "oot",
                "rows": len(y_oot),
                **metrics,
            }
        )

    return pd.DataFrame(metrics_rows), prediction_map


def build_calibration_before_after_report(
    y_true: pd.Series,
    prediction_map: dict[str, np.ndarray],
    n_bins: int = 10,
) -> pd.DataFrame:
    rows = []

    for model_name, scores in prediction_map.items():
        data = pd.DataFrame(
            {
                TARGET_DEFAULT_12M: y_true.to_numpy(),
                "predicted_pd": scores,
            }
        )

        unique_scores = data["predicted_pd"].nunique()
        bins = min(n_bins, unique_scores)

        if bins <= 1:
            data["pd_decile"] = 1
        else:
            data["pd_decile"] = pd.qcut(
                data["predicted_pd"],
                q=bins,
                labels=False,
                duplicates="drop",
            ) + 1

        grouped = (
            data.groupby("pd_decile", as_index=False)
            .agg(
                facilities=(TARGET_DEFAULT_12M, "size"),
                observed_defaults=(TARGET_DEFAULT_12M, "sum"),
                observed_default_rate=(TARGET_DEFAULT_12M, "mean"),
                avg_predicted_pd=("predicted_pd", "mean"),
                min_predicted_pd=("predicted_pd", "min"),
                max_predicted_pd=("predicted_pd", "max"),
            )
        )

        grouped["model"] = model_name
        grouped["calibration_error"] = grouped["avg_predicted_pd"] - grouped["observed_default_rate"]

        rows.append(grouped)

    if not rows:
        return pd.DataFrame()

    result = pd.concat(rows, ignore_index=True)
    return result[
        [
            "model",
            "pd_decile",
            "facilities",
            "observed_defaults",
            "observed_default_rate",
            "avg_predicted_pd",
            "min_predicted_pd",
            "max_predicted_pd",
            "calibration_error",
        ]
    ]
