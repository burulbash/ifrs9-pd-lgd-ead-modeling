from __future__ import annotations

import pandas as pd

from src.staging import (
    assign_ifrs9_stage,
    calculate_rating_downgrade,
    rating_to_order,
)


def test_rating_to_order() -> None:
    assert rating_to_order("A") == 1
    assert rating_to_order("C") == 3
    assert rating_to_order("F") == 6
    assert rating_to_order(None) is None


def test_calculate_rating_downgrade() -> None:
    assert calculate_rating_downgrade("A", "C") == 2
    assert calculate_rating_downgrade("D", "B") == -2
    assert calculate_rating_downgrade("B", "B") == 0


def test_stage_3_for_default_or_current_90dpd() -> None:
    df = pd.DataFrame(
        {
            "facility_id": ["F1", "F2"],
            "default_flag": [1, 0],
            "writeoff_flag": [0, 0],
            "current_dpd": [0, 95],
            "dpd_at_default": [0, 0],
            "watchlist_flag": [0, 0],
            "restructuring_flag": [0, 0],
            "pd_ratio_current_to_origination": [1.0, 1.0],
            "rating_downgrade_notches": [0, 0],
        }
    )

    result = assign_ifrs9_stage(df)

    assert result["ifrs9_stage"].tolist() == [3, 3]


def test_stage_2_for_sicr_rules() -> None:
    df = pd.DataFrame(
        {
            "facility_id": ["F1", "F2", "F3", "F4"],
            "default_flag": [0, 0, 0, 0],
            "writeoff_flag": [0, 0, 0, 0],
            "current_dpd": [0, 0, 35, 0],
            "dpd_at_default": [0, 0, 0, 0],
            "watchlist_flag": [0, 1, 0, 0],
            "restructuring_flag": [0, 0, 0, 1],
            "pd_ratio_current_to_origination": [2.2, 1.1, 1.0, 1.0],
            "rating_downgrade_notches": [0, 0, 0, 0],
        }
    )

    result = assign_ifrs9_stage(df)

    assert result["ifrs9_stage"].tolist() == [2, 2, 2, 2]


def test_stage_2_for_rating_downgrade() -> None:
    df = pd.DataFrame(
        {
            "facility_id": ["F1"],
            "default_flag": [0],
            "writeoff_flag": [0],
            "current_dpd": [0],
            "dpd_at_default": [0],
            "watchlist_flag": [0],
            "restructuring_flag": [0],
            "pd_ratio_current_to_origination": [1.1],
            "rating_downgrade_notches": [2],
        }
    )

    result = assign_ifrs9_stage(df)

    assert result.loc[0, "ifrs9_stage"] == 2
    assert result.loc[0, "ifrs9_stage_reason"] == "rating_downgrade_2plus"


def test_stage_1_for_performing_client() -> None:
    df = pd.DataFrame(
        {
            "facility_id": ["F1"],
            "default_flag": [0],
            "writeoff_flag": [0],
            "current_dpd": [0],
            "dpd_at_default": [0],
            "watchlist_flag": [0],
            "restructuring_flag": [0],
            "pd_ratio_current_to_origination": [1.2],
            "rating_downgrade_notches": [0],
        }
    )

    result = assign_ifrs9_stage(df)

    assert result.loc[0, "ifrs9_stage"] == 1
    assert result.loc[0, "ifrs9_stage_reason"] == "performing"
