from __future__ import annotations

import numpy as np
import pandas as pd

from src.financial_ratios import calculate_financial_ratios, safe_divide, winsorize_columns


def test_safe_divide_returns_nan_for_zero_denominator() -> None:
    numerator = pd.Series([10, 20, 30])
    denominator = pd.Series([2, 0, 5])

    result = safe_divide(numerator, denominator)

    assert result.iloc[0] == 5
    assert np.isnan(result.iloc[1])
    assert result.iloc[2] == 6


def test_calculate_financial_ratios_basic_values() -> None:
    df = pd.DataFrame(
        {
            "revenue": [1000],
            "revenue_prev_year": [800],
            "ebitda": [200],
            "net_income": [100],
            "total_assets": [2000],
            "current_assets": [600],
            "cash": [150],
            "inventory": [100],
            "total_liabilities": [1200],
            "current_liabilities": [300],
            "short_term_debt": [200],
            "long_term_debt": [400],
            "equity": [800],
            "interest_expense": [50],
            "operating_cash_flow": [180],
            "outstanding_amount": [500],
            "collateral_value": [1000],
        }
    )

    result = calculate_financial_ratios(df)

    assert result.loc[0, "total_debt"] == 600
    assert result.loc[0, "current_ratio"] == 2
    assert result.loc[0, "quick_ratio"] == 500 / 300
    assert result.loc[0, "debt_to_equity"] == 600 / 800
    assert result.loc[0, "debt_to_assets"] == 600 / 2000
    assert result.loc[0, "debt_to_ebitda"] == 3
    assert result.loc[0, "interest_coverage"] == 4
    assert result.loc[0, "ebitda_margin"] == 0.2
    assert result.loc[0, "net_profit_margin"] == 0.1
    assert result.loc[0, "revenue_growth_yoy"] == 0.25
    assert result.loc[0, "loan_to_value"] == 0.5
    assert result.loc[0, "collateral_coverage"] == 2


def test_winsorize_columns_clips_extreme_values() -> None:
    df = pd.DataFrame({"ratio": [1, 2, 3, 1000]})

    result = winsorize_columns(df, ["ratio"], lower_quantile=0.0, upper_quantile=0.75)

    assert result["ratio"].max() <= df["ratio"].quantile(0.75)
