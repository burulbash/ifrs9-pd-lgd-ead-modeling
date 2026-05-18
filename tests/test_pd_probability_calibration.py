from __future__ import annotations

import numpy as np
import pandas as pd

from src.pd_probability_calibration import build_calibration_before_after_report


def test_build_calibration_before_after_report() -> None:
    y_true = pd.Series([0, 0, 1, 0, 1, 0, 0, 1])

    prediction_map = {
        "raw": np.array([0.01, 0.02, 0.15, 0.03, 0.20, 0.04, 0.05, 0.25]),
        "sigmoid": np.array([0.03, 0.04, 0.12, 0.05, 0.18, 0.06, 0.07, 0.22]),
    }

    report = build_calibration_before_after_report(
        y_true=y_true,
        prediction_map=prediction_map,
        n_bins=4,
    )

    assert {"model", "pd_decile", "observed_default_rate", "avg_predicted_pd"}.issubset(report.columns)
    assert set(report["model"]) == {"raw", "sigmoid"}
    assert report["pd_decile"].min() >= 1


def test_fit_prefit_calibrator_returns_probabilities() -> None:
    from sklearn.linear_model import LogisticRegression

    from src.pd_probability_calibration import (
        fit_prefit_calibrator,
        predict_positive_proba,
    )

    X_train = pd.DataFrame(
        {
            "x1": [
                0.00, 0.05, 0.10, 0.15, 0.20,
                0.80, 0.85, 0.90, 0.95, 1.00,
            ],
            "x2": [
                1.00, 0.95, 0.90, 0.85, 0.80,
                0.20, 0.15, 0.10, 0.05, 0.00,
            ],
        }
    )
    y_train = pd.Series([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])

    model = LogisticRegression()
    model.fit(X_train, y_train)

    calibrator = fit_prefit_calibrator(
        fitted_model=model,
        X_valid=X_train,
        y_valid=y_train,
        method="sigmoid",
    )

    scores = predict_positive_proba(calibrator, X_train)

    assert len(scores) == len(X_train)
    assert ((scores >= 0) & (scores <= 1)).all()
