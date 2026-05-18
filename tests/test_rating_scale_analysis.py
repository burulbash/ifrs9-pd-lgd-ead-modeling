from __future__ import annotations

import pandas as pd

from src.rating_scale_analysis import (
    build_alternative_rating_backtesting,
    build_alternative_rating_mapping,
)


def test_build_alternative_rating_mapping_merges_sparse_f() -> None:
    rating_summary = pd.DataFrame(
        {
            "rating_grade": ["A", "E", "F"],
            "facilities": [100, 80, 10],
            "observed_defaults": [1, 12, 0],
            "observed_default_rate": [0.01, 0.15, 0.0],
            "avg_predicted_pd": [0.003, 0.10, 0.25],
            "min_predicted_pd": [0.001, 0.08, 0.20],
            "max_predicted_pd": [0.004, 0.14, 0.30],
        }
    )

    mapping = build_alternative_rating_mapping(rating_summary, min_bucket_size=50)

    assert "E_F" in set(mapping["alternative_rating_grade"])
    assert mapping.loc[mapping["original_rating_grade"].eq("F"), "alternative_rating_grade"].iloc[0] == "E_F"


def test_build_alternative_rating_backtesting() -> None:
    rating_summary = pd.DataFrame(
        {
            "rating_grade": ["E", "F"],
            "facilities": [80, 10],
            "observed_defaults": [12, 0],
            "observed_default_rate": [0.15, 0.0],
            "avg_predicted_pd": [0.10, 0.25],
            "min_predicted_pd": [0.08, 0.20],
            "max_predicted_pd": [0.14, 0.30],
        }
    )

    mapping = build_alternative_rating_mapping(rating_summary, min_bucket_size=50)
    backtesting = build_alternative_rating_backtesting(rating_summary, mapping)

    assert len(backtesting) == 1
    assert backtesting["alternative_rating_grade"].iloc[0] == "E_F"
    assert backtesting["facilities"].iloc[0] == 90
    assert backtesting["observed_defaults"].iloc[0] == 12
