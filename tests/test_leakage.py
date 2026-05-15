from __future__ import annotations

import pandas as pd

from src.leakage import build_leakage_exclusion_report, classify_leakage_column


def test_classify_leakage_column_detects_target() -> None:
    result = classify_leakage_column("target_default_12m")

    assert result is not None
    assert result[0] == "target"


def test_classify_leakage_column_detects_recovery_outcome() -> None:
    result = classify_leakage_column("total_recovery_amount")

    assert result is not None
    assert result[0] == "recovery_outcome"


def test_classify_leakage_column_allows_regular_feature() -> None:
    result = classify_leakage_column("debt_to_ebitda")

    assert result is None


def test_build_leakage_exclusion_report() -> None:
    df = pd.DataFrame(
        {
            "facility_id": ["F1", "F2"],
            "observation_date": ["2025-01-01", "2025-01-01"],
            "target_default_12m": [0, 1],
            "default_date": [None, "2025-06-01"],
            "total_recovery_amount": [0, 100],
            "debt_to_ebitda": [2.0, 5.0],
        }
    )

    report = build_leakage_exclusion_report(df)

    assert set(report.columns) == {"column", "reason", "category"}
    assert "target_default_12m" in set(report["column"])
    assert "debt_to_ebitda" not in set(report["column"])
    assert set(report["category"]).issuperset({"id", "date", "target", "default_outcome", "recovery_outcome"})
