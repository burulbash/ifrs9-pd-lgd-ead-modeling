from __future__ import annotations

import pandas as pd

from src.train_pd_model import (
    assign_pd_rating_grade,
    build_rating_summary,
    get_pd_feature_columns,
)


def test_assign_pd_rating_grade() -> None:
    assert assign_pd_rating_grade(0.001) == "A"
    assert assign_pd_rating_grade(0.010) == "B"
    assert assign_pd_rating_grade(0.025) == "C"
    assert assign_pd_rating_grade(0.050) == "D"
    assert assign_pd_rating_grade(0.100) == "E"
    assert assign_pd_rating_grade(0.200) == "F"


def test_get_pd_feature_columns_excludes_targets_and_leakage() -> None:
    df = pd.DataFrame(
        {
            "facility_id": ["F1"],
            "company_id": ["C1"],
            "observation_date": ["2024-01-01"],
            "target_default_12m": [1],
            "default_date": ["2024-06-01"],
            "realized_lgd": [0.5],
            "revenue": [1000],
            "current_ratio": [1.5],
        }
    )

    features, suspicious = get_pd_feature_columns(df)

    assert "revenue" in features
    assert "current_ratio" in features
    assert "target_default_12m" not in features
    assert "default_date" not in features
    assert "realized_lgd" not in features
    assert suspicious == []


def test_build_rating_summary() -> None:
    predictions = pd.DataFrame(
        {
            "facility_id": ["F1", "F2", "F3"],
            "target_default_12m": [0, 0, 1],
            "pd_model": [0.002, 0.030, 0.200],
        }
    )

    summary = build_rating_summary(predictions, pd_column="pd_model")

    assert set(summary["rating_grade"]) == {"A", "B", "C", "D", "E", "F"}
    assert summary["facilities"].sum() == 3
    assert summary["observed_defaults"].sum() == 1
