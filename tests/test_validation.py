from __future__ import annotations

import pandas as pd

from src.validation import (
    build_pd_backtesting_by_rating,
    build_pd_calibration_by_decile,
    calculate_psi,
    check_rating_monotonicity,
)


def test_build_pd_backtesting_by_rating() -> None:
    predictions = pd.DataFrame(
        {
            "facility_id": ["F1", "F2", "F3", "F4"],
            "target_default_12m": [0, 0, 1, 1],
            "pd_model": [0.002, 0.020, 0.080, 0.200],
        }
    )

    report = build_pd_backtesting_by_rating(
        predictions,
        pd_column="pd_model",
    )

    assert report["facilities"].sum() == 4
    assert report["defaults"].sum() == 2
    assert "calibration_error" in report.columns


def test_check_rating_monotonicity_detects_violation() -> None:
    rating_report = pd.DataFrame(
        {
            "rating_grade": ["A", "B", "C"],
            "facilities": [100, 100, 100],
            "observed_default_rate": [0.01, 0.05, 0.03],
        }
    )

    summary, violations = check_rating_monotonicity(rating_report)

    assert bool(summary.loc[0, "is_monotonic"]) is False
    assert summary.loc[0, "violations_count"] == 1
    assert len(violations) == 1


def test_build_pd_calibration_by_decile() -> None:
    predictions = pd.DataFrame(
        {
            "facility_id": [f"F{i}" for i in range(10)],
            "target_default_12m": [0, 0, 0, 0, 0, 1, 0, 1, 0, 1],
            "pd_model": [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10],
        }
    )

    report = build_pd_calibration_by_decile(
        predictions,
        pd_column="pd_model",
        n_bins=5,
    )

    assert report["facilities"].sum() == 10
    assert "avg_predicted_pd" in report.columns
    assert "observed_default_rate" in report.columns


def test_calculate_psi_zero_when_distributions_are_equal() -> None:
    expected = pd.Series([1, 2, 3, 4, 5])
    actual = pd.Series([1, 2, 3, 4, 5])

    psi, details = calculate_psi(expected, actual, bins=5)

    assert round(psi, 8) == 0
    assert details["expected_count"].sum() == 5
    assert details["actual_count"].sum() == 5


def test_calculate_psi_positive_when_distribution_shifts() -> None:
    expected = pd.Series([1, 2, 3, 4, 5, 6, 7, 8])
    actual = pd.Series([10, 11, 12, 13, 14, 15, 16, 17])

    psi, _ = calculate_psi(expected, actual, bins=4)

    assert psi > 0


def test_build_rating_binomial_backtesting() -> None:
    from src.validation import build_rating_binomial_backtesting

    rating_report = pd.DataFrame(
        {
            "rating_grade": ["A", "B"],
            "facilities": [100, 100],
            "defaults": [1, 10],
            "observed_default_rate": [0.01, 0.10],
            "avg_predicted_pd": [0.01, 0.03],
            "min_predicted_pd": [0.001, 0.02],
            "max_predicted_pd": [0.02, 0.04],
            "calibration_error": [0.0, -0.07],
        }
    )

    report = build_rating_binomial_backtesting(rating_report)

    assert "expected_defaults" in report.columns
    assert "binomial_p_value" in report.columns
    assert "traffic_light" in report.columns
    assert report["expected_defaults"].iloc[0] == 1
    assert set(report["traffic_light"]).issubset({"GREEN", "AMBER", "RED", "UNKNOWN"})
