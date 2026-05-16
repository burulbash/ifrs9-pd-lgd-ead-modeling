from __future__ import annotations

import pandas as pd

from src.outlier_diagnostics import (
    build_ead_ccf_outlier_report,
    build_lgd_outlier_report,
)


def test_build_lgd_outlier_report_detects_invalid_values() -> None:
    df = pd.DataFrame(
        {
            "realized_lgd": [0.2, 1.2],
            "ead_at_default": [1000, 2000],
            "total_recovery_amount": [500, 2500],
            "total_collection_cost": [20, -10],
        }
    )

    report = build_lgd_outlier_report(df)

    assert set(report.columns) == {"area", "check_name", "metric_name", "metric_value", "status", "details"}
    assert "FAIL" in set(report["status"])


def test_build_ead_ccf_outlier_report_detects_invalid_values() -> None:
    df = pd.DataFrame(
        {
            "realized_ccf": [0.5, 2.0],
            "ead_at_default": [1000, 2000],
            "undrawn_amount": [500, 0],
            "outstanding_amount": [300, -1],
            "limit_amount": [1000, 1000],
        }
    )

    report = build_ead_ccf_outlier_report(df)

    assert set(report.columns) == {"area", "check_name", "metric_name", "metric_value", "status", "details"}
    assert "FAIL" in set(report["status"])
