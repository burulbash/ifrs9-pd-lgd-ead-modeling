from __future__ import annotations

import pandas as pd

from src.stress_scenarios import (
    calculate_stress_scenario_ecl,
    get_industry_stress_multiplier,
)


def test_get_industry_stress_multiplier_higher_for_construction() -> None:
    industries = pd.Series(["construction", "services"])

    result = get_industry_stress_multiplier(
        industries,
        scenario_name="downside",
        scenario_industry_multiplier=1.15,
    )

    assert result.iloc[0] > result.iloc[1]


def test_fx_shock_adds_extra_for_fx_sensitive_industry() -> None:
    industries = pd.Series(["trade", "services"])

    result = get_industry_stress_multiplier(
        industries,
        scenario_name="fx_shock",
        scenario_industry_multiplier=1.15,
    )

    assert result.iloc[0] > result.iloc[1]


def test_calculate_stress_scenario_ecl_outputs_reports() -> None:
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
            "industry": ["construction", "services", "trade"],
        }
    )

    stress_df, scenario_summary, by_stage, by_industry = calculate_stress_scenario_ecl(df)

    assert "stress_ecl_base" in stress_df.columns
    assert "stress_ecl_downside" in stress_df.columns
    assert "stress_ecl_severe_downturn" in stress_df.columns

    assert set(["base", "downside", "severe_downturn"]).issubset(set(scenario_summary["scenario"]))
    assert scenario_summary["total_ecl"].sum() > 0
    assert by_stage["facilities"].sum() > 0
    assert by_industry["facilities"].sum() > 0


def test_severe_downturn_ecl_is_above_base() -> None:
    df = pd.DataFrame(
        {
            "facility_id": ["F1", "F2"],
            "reporting_date": ["2025-12-31", "2025-12-31"],
            "maturity_date": ["2027-12-31", "2027-12-31"],
            "ifrs9_stage": [1, 2],
            "current_pd_estimate": [0.03, 0.06],
            "origination_pd_estimate": [0.02, 0.03],
            "current_outstanding_balance": [1000, 2000],
            "outstanding_amount": [1000, 2000],
            "undrawn_amount": [500, 1000],
            "revolving_flag": [1, 1],
            "product_type": ["credit_line", "overdraft"],
            "effective_collateral_coverage": [0.8, 0.5],
            "collateral_type": ["real_estate", "equipment"],
            "industry": ["construction", "trade"],
        }
    )

    _, scenario_summary, _, _ = calculate_stress_scenario_ecl(df)

    base_ecl = scenario_summary.loc[scenario_summary["scenario"].eq("base"), "total_ecl"].iloc[0]
    severe_ecl = scenario_summary.loc[scenario_summary["scenario"].eq("severe_downturn"), "total_ecl"].iloc[0]

    assert severe_ecl > base_ecl
