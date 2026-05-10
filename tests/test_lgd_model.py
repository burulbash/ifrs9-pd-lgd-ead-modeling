from __future__ import annotations

import pandas as pd

from src.train_lgd_model import (
    build_lgd_calibration_by_decile,
    build_lgd_segment_report,
    clip_lgd_values,
    get_lgd_feature_columns,
)


def test_clip_lgd_values_bounds_values() -> None:
    values = pd.Series([-0.2, 0.4, 1.3])

    result = clip_lgd_values(values)

    assert result.tolist() == [0.0, 0.4, 1.0]


def test_get_lgd_feature_columns_excludes_recovery_leakage() -> None:
    df = pd.DataFrame(
        {
            "facility_id": ["F1"],
            "company_id": ["C1"],
            "default_date": ["2024-01-01"],
            "realized_lgd": [0.4],
            "total_recovery_amount": [100],
            "net_recovery_amount": [90],
            "product_type": ["term_loan"],
            "collateral_coverage": [1.5],
        }
    )

    features = get_lgd_feature_columns(df)

    assert "product_type" in features
    assert "collateral_coverage" in features
    assert "realized_lgd" not in features
    assert "total_recovery_amount" not in features
    assert "net_recovery_amount" not in features


def test_build_lgd_segment_report() -> None:
    df = pd.DataFrame(
        {
            "facility_id": ["F1", "F2", "F3"],
            "product_type": ["term_loan", "term_loan", "credit_line"],
            "realized_lgd": [0.2, 0.4, 0.8],
            "lgd_model": [0.3, 0.5, 0.7],
            "ead_at_default": [100, 200, 300],
        }
    )

    report = build_lgd_segment_report(
        df,
        actual_col="realized_lgd",
        pred_col="lgd_model",
        segment_col="product_type",
    )

    assert set(report["segment"]) == {"term_loan", "credit_line"}
    assert report["facilities"].sum() == 3
    assert "prediction_error" in report.columns


def test_build_lgd_calibration_by_decile() -> None:
    df = pd.DataFrame(
        {
            "facility_id": [f"F{i}" for i in range(10)],
            "realized_lgd": [0.1, 0.2, 0.2, 0.3, 0.4, 0.5, 0.5, 0.6, 0.7, 0.8],
            "lgd_model": [0.1, 0.15, 0.25, 0.35, 0.45, 0.55, 0.58, 0.62, 0.72, 0.82],
            "ead_at_default": [100] * 10,
        }
    )

    report = build_lgd_calibration_by_decile(
        df,
        actual_col="realized_lgd",
        pred_col="lgd_model",
        n_bins=5,
    )

    assert report["facilities"].sum() == 10
    assert "avg_actual_lgd" in report.columns
    assert "avg_predicted_lgd" in report.columns
