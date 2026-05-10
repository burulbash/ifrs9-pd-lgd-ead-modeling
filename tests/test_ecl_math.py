from __future__ import annotations

import pandas as pd

from src.ecl import (
    calculate_12m_ecl,
    calculate_ifrs9_ecl,
    calculate_lifetime_pd,
    calculate_scenario_weighted_ecl,
    calculate_stage_ecl,
)


def test_calculate_lifetime_pd() -> None:
    annual_pd = pd.Series([0.10])
    years = pd.Series([2.0])

    result = calculate_lifetime_pd(annual_pd, years)

    assert round(result.iloc[0], 4) == 0.19


def test_calculate_12m_ecl() -> None:
    pd_12m = pd.Series([0.10])
    lgd = pd.Series([0.50])
    ead = pd.Series([1000])

    result = calculate_12m_ecl(pd_12m, lgd, ead)

    assert result.iloc[0] == 50


def test_calculate_stage_ecl() -> None:
    stage = pd.Series([1, 2, 3])
    pd_12m = pd.Series([0.10, 0.10, 0.10])
    lifetime_pd = pd.Series([0.20, 0.20, 0.20])
    lgd = pd.Series([0.50, 0.50, 0.50])
    ead = pd.Series([1000, 1000, 1000])

    result = calculate_stage_ecl(stage, pd_12m, lifetime_pd, lgd, ead)

    assert result.tolist() == [50, 100, 500]


def test_calculate_scenario_weighted_ecl() -> None:
    df = pd.DataFrame(
        {
            "ecl_base": [100],
            "ecl_downside": [150],
            "ecl_upside": [80],
        }
    )

    result = calculate_scenario_weighted_ecl(
        df,
        scenario_ecl_columns={
            "base": "ecl_base",
            "downside": "ecl_downside",
            "upside": "ecl_upside",
        },
        scenario_weights={
            "base": 0.60,
            "downside": 0.25,
            "upside": 0.15,
        },
    )

    assert result.iloc[0] == 109.5


def test_calculate_ifrs9_ecl_basic_columns() -> None:
    df = pd.DataFrame(
        {
            "facility_id": ["F1", "F2", "F3"],
            "reporting_date": ["2025-12-31", "2025-12-31", "2025-12-31"],
            "maturity_date": ["2026-12-31", "2027-12-31", "2026-06-30"],
            "ifrs9_stage": [1, 2, 3],
            "current_pd_estimate": [0.02, 0.05, 0.20],
            "origination_pd_estimate": [0.01, 0.02, 0.10],
            "current_outstanding_balance": [1000, 2000, 3000],
            "outstanding_amount": [1000, 2000, 3000],
            "undrawn_amount": [500, 1000, 0],
            "revolving_flag": [1, 1, 0],
            "product_type": ["credit_line", "overdraft", "term_loan"],
            "effective_collateral_coverage": [1.0, 0.5, 0.0],
            "collateral_type": ["real_estate", "equipment", "none"],
        }
    )

    result, scenario_summary = calculate_ifrs9_ecl(
        df,
        scenario_weights={
            "base": 0.60,
            "downside": 0.25,
            "upside": 0.15,
        },
    )

    assert "scenario_weighted_ecl" in result.columns
    assert "ecl_base" in result.columns
    assert "ecl_downside" in result.columns
    assert "ecl_upside" in result.columns
    assert result["scenario_weighted_ecl"].sum() > 0
    assert set(scenario_summary["scenario"]) == {"base", "downside", "upside"}
