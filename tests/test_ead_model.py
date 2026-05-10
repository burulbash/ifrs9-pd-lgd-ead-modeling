from __future__ import annotations

import pandas as pd

from src.train_ead_ccf_model import (
    build_ead_by_product_report,
    build_ead_calibration_by_decile,
    clip_ccf_values,
    get_ead_feature_columns,
)


def test_clip_ccf_values_bounds_values() -> None:
    values = pd.Series([-0.2, 0.4, 2.0])

    result = clip_ccf_values(values)

    assert result.tolist() == [0.0, 0.4, 1.5]


def test_get_ead_feature_columns_excludes_outcome_leakage() -> None:
    df = pd.DataFrame(
        {
            "facility_id": ["F1"],
            "company_id": ["C1"],
            "default_date": ["2024-01-01"],
            "realized_ccf": [0.4],
            "ead_at_default": [100],
            "writeoff_flag": [0],
            "product_type": ["credit_line"],
            "utilization_rate": [0.7],
        }
    )

    features = get_ead_feature_columns(df)

    assert "product_type" in features
    assert "utilization_rate" in features
    assert "realized_ccf" not in features
    assert "ead_at_default" not in features
    assert "writeoff_flag" not in features


def test_build_ead_by_product_report() -> None:
    df = pd.DataFrame(
        {
            "facility_id": ["F1", "F2", "F3"],
            "product_type": ["credit_line", "credit_line", "overdraft"],
            "realized_ccf": [0.2, 0.4, 0.8],
            "ccf_model": [0.3, 0.5, 0.7],
            "ead_at_default": [100, 200, 300],
        }
    )

    report = build_ead_by_product_report(
        df,
        actual_col="realized_ccf",
        pred_col="ccf_model",
    )

    assert set(report["product_type"]) == {"credit_line", "overdraft"}
    assert report["facilities"].sum() == 3
    assert "prediction_error" in report.columns


def test_build_ead_calibration_by_decile() -> None:
    df = pd.DataFrame(
        {
            "facility_id": [f"F{i}" for i in range(10)],
            "realized_ccf": [0.1, 0.2, 0.2, 0.3, 0.4, 0.5, 0.5, 0.6, 0.7, 0.8],
            "ccf_model": [0.1, 0.15, 0.25, 0.35, 0.45, 0.55, 0.58, 0.62, 0.72, 0.82],
            "ead_at_default": [100] * 10,
        }
    )

    report = build_ead_calibration_by_decile(
        df,
        actual_col="realized_ccf",
        pred_col="ccf_model",
        n_bins=5,
    )

    assert report["facilities"].sum() == 10
    assert "avg_actual_ccf" in report.columns
    assert "avg_predicted_ccf" in report.columns
