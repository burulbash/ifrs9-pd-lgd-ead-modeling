from __future__ import annotations

import numpy as np
import pandas as pd


SCENARIO_FACTORS = {
    "base": {
        "pd_multiplier": 1.00,
        "lgd_multiplier": 1.00,
        "ccf_multiplier": 1.00,
    },
    "downside": {
        "pd_multiplier": 1.35,
        "lgd_multiplier": 1.10,
        "ccf_multiplier": 1.15,
    },
    "upside": {
        "pd_multiplier": 0.85,
        "lgd_multiplier": 0.95,
        "ccf_multiplier": 0.90,
    },
}


def clip_probability(values) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.clip(lower=0, upper=1)


def calculate_lifetime_pd(
    annual_pd,
    remaining_life_years,
) -> pd.Series:
    annual_pd_clean = clip_probability(annual_pd)
    years_clean = pd.to_numeric(remaining_life_years, errors="coerce").fillna(1.0)
    years_clean = years_clean.clip(lower=0.0)

    lifetime_pd = 1 - (1 - annual_pd_clean) ** years_clean

    return clip_probability(lifetime_pd)


def calculate_12m_ecl(
    pd_12m,
    lgd,
    ead,
) -> pd.Series:
    pd_12m_clean = clip_probability(pd_12m)
    lgd_clean = clip_probability(lgd)
    ead_clean = pd.to_numeric(ead, errors="coerce").fillna(0).clip(lower=0)

    return pd_12m_clean * lgd_clean * ead_clean


def calculate_lifetime_ecl(
    lifetime_pd,
    lgd,
    ead,
) -> pd.Series:
    lifetime_pd_clean = clip_probability(lifetime_pd)
    lgd_clean = clip_probability(lgd)
    ead_clean = pd.to_numeric(ead, errors="coerce").fillna(0).clip(lower=0)

    return lifetime_pd_clean * lgd_clean * ead_clean


def calculate_stage_ecl(
    stage,
    pd_12m,
    lifetime_pd,
    lgd,
    ead,
) -> pd.Series:
    stage_clean = pd.to_numeric(stage, errors="coerce").fillna(1).astype(int)

    stage_1_ecl = calculate_12m_ecl(pd_12m, lgd, ead)
    stage_2_ecl = calculate_lifetime_ecl(lifetime_pd, lgd, ead)
    stage_3_ecl = calculate_lifetime_ecl(pd.Series([1.0] * len(stage_clean)), lgd, ead)

    return pd.Series(
        np.select(
            [
                stage_clean == 1,
                stage_clean == 2,
                stage_clean == 3,
            ],
            [
                stage_1_ecl,
                stage_2_ecl,
                stage_3_ecl,
            ],
            default=stage_1_ecl,
        ),
        index=stage_clean.index,
    )


def calculate_scenario_weighted_ecl(
    df: pd.DataFrame,
    scenario_ecl_columns: dict[str, str],
    scenario_weights: dict[str, float],
) -> pd.Series:
    weighted_ecl = pd.Series(0.0, index=df.index)

    for scenario, column in scenario_ecl_columns.items():
        weight = scenario_weights.get(scenario, 0.0)
        weighted_ecl += pd.to_numeric(df[column], errors="coerce").fillna(0) * weight

    return weighted_ecl


def estimate_lgd_from_collateral(df: pd.DataFrame) -> pd.Series:
    coverage = pd.to_numeric(
        df.get("effective_collateral_coverage", df.get("collateral_coverage", 0)),
        errors="coerce",
    ).fillna(0)

    collateral_type = df.get("collateral_type", pd.Series(["none"] * len(df), index=df.index))
    is_unsecured = collateral_type.fillna("none").astype(str).str.lower().eq("none")

    base_lgd = 0.72 - 0.28 * coverage.clip(lower=0, upper=2.5)
    base_lgd = base_lgd + np.where(is_unsecured, 0.12, 0.0)

    return pd.Series(base_lgd, index=df.index).clip(lower=0.05, upper=0.95)


def estimate_ccf(df: pd.DataFrame) -> pd.Series:
    product_type = df.get("product_type", pd.Series(["term_loan"] * len(df), index=df.index))
    product_type = product_type.fillna("term_loan").astype(str)

    revolving_flag = pd.to_numeric(df.get("revolving_flag", 0), errors="coerce").fillna(0)

    ccf = pd.Series(0.0, index=df.index)

    ccf.loc[product_type.eq("credit_line")] = 0.45
    ccf.loc[product_type.eq("overdraft")] = 0.75
    ccf.loc[product_type.eq("trade_finance")] = 0.35
    ccf.loc[revolving_flag.eq(1) & ccf.eq(0)] = 0.40

    return ccf.clip(lower=0, upper=1.5)


def prepare_ecl_base_columns(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()

    reporting_date = pd.to_datetime(data["reporting_date"], errors="coerce")
    maturity_date = pd.to_datetime(data["maturity_date"], errors="coerce")

    remaining_life_years = (maturity_date - reporting_date).dt.days / 365.25
    data["remaining_life_years"] = remaining_life_years.clip(lower=0.25).fillna(1.0)

    current_pd = pd.to_numeric(data.get("current_pd_estimate"), errors="coerce")
    origination_pd = pd.to_numeric(data.get("origination_pd_estimate"), errors="coerce")

    data["pd_12m_base"] = clip_probability(
        current_pd.fillna(origination_pd).fillna(0.02)
    )

    data["lgd_base"] = estimate_lgd_from_collateral(data)
    data["ccf_base"] = estimate_ccf(data)

    current_outstanding = pd.to_numeric(
        data.get("current_outstanding_balance", data.get("outstanding_amount", 0)),
        errors="coerce",
    ).fillna(0).clip(lower=0)

    undrawn_amount = pd.to_numeric(data.get("undrawn_amount", 0), errors="coerce").fillna(0).clip(lower=0)

    data["ead_base"] = current_outstanding + data["ccf_base"] * undrawn_amount

    return data


def calculate_ifrs9_ecl(
    df: pd.DataFrame,
    scenario_weights: dict[str, float],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = prepare_ecl_base_columns(df)

    scenario_rows = []
    scenario_ecl_columns = {}

    for scenario, factors in SCENARIO_FACTORS.items():
        pd_col = f"pd_12m_{scenario}"
        lifetime_pd_col = f"lifetime_pd_{scenario}"
        lgd_col = f"lgd_{scenario}"
        ccf_col = f"ccf_{scenario}"
        ead_col = f"ead_{scenario}"
        ecl_col = f"ecl_{scenario}"

        data[pd_col] = clip_probability(data["pd_12m_base"] * factors["pd_multiplier"])
        data[lifetime_pd_col] = calculate_lifetime_pd(
            data[pd_col],
            data["remaining_life_years"],
        )
        data[lgd_col] = clip_probability(data["lgd_base"] * factors["lgd_multiplier"])
        data[ccf_col] = pd.to_numeric(data["ccf_base"] * factors["ccf_multiplier"], errors="coerce").clip(lower=0, upper=1.5)

        current_outstanding = pd.to_numeric(
            data.get("current_outstanding_balance", data.get("outstanding_amount", 0)),
            errors="coerce",
        ).fillna(0).clip(lower=0)

        undrawn_amount = pd.to_numeric(data.get("undrawn_amount", 0), errors="coerce").fillna(0).clip(lower=0)

        data[ead_col] = current_outstanding + data[ccf_col] * undrawn_amount

        data[ecl_col] = calculate_stage_ecl(
            stage=data["ifrs9_stage"],
            pd_12m=data[pd_col],
            lifetime_pd=data[lifetime_pd_col],
            lgd=data[lgd_col],
            ead=data[ead_col],
        )

        scenario_ecl_columns[scenario] = ecl_col

        scenario_rows.append(
            {
                "scenario": scenario,
                "scenario_weight": scenario_weights.get(scenario, 0.0),
                "total_ecl": data[ecl_col].sum(),
                "avg_ecl": data[ecl_col].mean(),
                "total_ead": data[ead_col].sum(),
                "avg_pd_12m": data[pd_col].mean(),
                "avg_lgd": data[lgd_col].mean(),
            }
        )

    data["scenario_weighted_ecl"] = calculate_scenario_weighted_ecl(
        data,
        scenario_ecl_columns=scenario_ecl_columns,
        scenario_weights=scenario_weights,
    )

    scenario_summary = pd.DataFrame(scenario_rows)

    return data, scenario_summary


def build_ecl_by_stage(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("ifrs9_stage", as_index=False)
        .agg(
            facilities=("facility_id", "size"),
            total_ead=("ead_base", "sum"),
            total_ecl=("scenario_weighted_ecl", "sum"),
            avg_ecl=("scenario_weighted_ecl", "mean"),
            avg_pd_12m=("pd_12m_base", "mean"),
            avg_lgd=("lgd_base", "mean"),
        )
        .sort_values("ifrs9_stage")
    )


def build_ecl_by_rating(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("current_rating_grade", dropna=False, as_index=False)
        .agg(
            facilities=("facility_id", "size"),
            total_ead=("ead_base", "sum"),
            total_ecl=("scenario_weighted_ecl", "sum"),
            avg_ecl=("scenario_weighted_ecl", "mean"),
            avg_pd_12m=("pd_12m_base", "mean"),
            avg_lgd=("lgd_base", "mean"),
        )
        .sort_values("current_rating_grade")
    )


def build_ecl_by_industry(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("industry", dropna=False, as_index=False)
        .agg(
            facilities=("facility_id", "size"),
            total_ead=("ead_base", "sum"),
            total_ecl=("scenario_weighted_ecl", "sum"),
            avg_ecl=("scenario_weighted_ecl", "mean"),
            avg_pd_12m=("pd_12m_base", "mean"),
            avg_lgd=("lgd_base", "mean"),
        )
        .sort_values("total_ecl", ascending=False)
    )


def build_ecl_portfolio_summary(df: pd.DataFrame) -> pd.DataFrame:
    total_ead = df["ead_base"].sum()
    total_ecl = df["scenario_weighted_ecl"].sum()

    return pd.DataFrame(
        [
            {
                "facilities": len(df),
                "total_ead": total_ead,
                "total_ecl": total_ecl,
                "ecl_rate": total_ecl / total_ead if total_ead else 0,
                "avg_pd_12m": df["pd_12m_base"].mean(),
                "avg_lgd": df["lgd_base"].mean(),
                "stage_1_share": (df["ifrs9_stage"] == 1).mean(),
                "stage_2_share": (df["ifrs9_stage"] == 2).mean(),
                "stage_3_share": (df["ifrs9_stage"] == 3).mean(),
            }
        ]
    )
