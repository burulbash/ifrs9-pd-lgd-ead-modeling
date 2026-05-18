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
