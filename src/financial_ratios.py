from __future__ import annotations

import numpy as np
import pandas as pd


def safe_divide(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    """Divide two numeric series and return NaN when denominator is zero or missing."""

    numerator_clean = pd.to_numeric(numerator, errors="coerce")
    denominator_clean = pd.to_numeric(denominator, errors="coerce").replace(0, np.nan)

    result = numerator_clean / denominator_clean

    return result.replace([np.inf, -np.inf], np.nan)


def calculate_financial_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate basic SME/corporate financial ratios.

    The input is expected to contain financial statement fields and, when available,
    facility/collateral fields.
    """

    data = df.copy()

    data["total_debt"] = (
        pd.to_numeric(data.get("short_term_debt", 0), errors="coerce").fillna(0)
        + pd.to_numeric(data.get("long_term_debt", 0), errors="coerce").fillna(0)
    )

    data["current_ratio"] = safe_divide(
        data["current_assets"],
        data["current_liabilities"],
    )

    data["quick_ratio"] = safe_divide(
        data["current_assets"] - data.get("inventory", 0),
        data["current_liabilities"],
    )

    data["debt_to_equity"] = safe_divide(
        data["total_debt"],
        data["equity"],
    )

    data["debt_to_assets"] = safe_divide(
        data["total_debt"],
        data["total_assets"],
    )

    data["debt_to_ebitda"] = safe_divide(
        data["total_debt"],
        data["ebitda"],
    )

    data["interest_coverage"] = safe_divide(
        data["ebitda"],
        data["interest_expense"],
    )

    data["ebitda_margin"] = safe_divide(
        data["ebitda"],
        data["revenue"],
    )

    data["net_profit_margin"] = safe_divide(
        data["net_income"],
        data["revenue"],
    )

    data["operating_cf_to_debt"] = safe_divide(
        data["operating_cash_flow"],
        data["total_debt"],
    )

    data["cash_to_short_term_debt"] = safe_divide(
        data["cash"],
        data["short_term_debt"],
    )

    data["equity_to_assets"] = safe_divide(
        data["equity"],
        data["total_assets"],
    )

    if {"revenue", "revenue_prev_year"}.issubset(data.columns):
        data["revenue_growth_yoy"] = safe_divide(
            data["revenue"] - data["revenue_prev_year"],
            data["revenue_prev_year"],
        )

    if {"outstanding_amount", "collateral_value"}.issubset(data.columns):
        data["loan_to_value"] = safe_divide(
            data["outstanding_amount"],
            data["collateral_value"],
        )

        data["collateral_coverage"] = safe_divide(
            data["collateral_value"],
            data["outstanding_amount"],
        )

    return data


def winsorize_columns(
    df: pd.DataFrame,
    columns: list[str],
    lower_quantile: float = 0.01,
    upper_quantile: float = 0.99,
) -> pd.DataFrame:
    """Clip extreme values in selected columns by quantiles."""

    data = df.copy()

    for column in columns:
        if column not in data.columns:
            continue

        lower = data[column].quantile(lower_quantile)
        upper = data[column].quantile(upper_quantile)

        data[column] = data[column].clip(lower=lower, upper=upper)

    return data
