from __future__ import annotations

import pandas as pd


ID_COLUMNS = {
    "company_id",
    "facility_id",
    "payment_id",
    "collateral_id",
    "recovery_id",
    "loan_id",
    "application_id",
    "client_id",
}

DATE_COLUMNS = {
    "observation_date",
    "reporting_date",
    "report_date",
    "origination_date",
    "maturity_date",
    "payment_date",
    "default_date",
    "recovery_date",
    "valuation_date",
    "rating_date",
}

TARGET_COLUMNS = {
    "target_default_12m",
    "target_default_90dpd_12m",
    "target_ever30_6m",
}

FUTURE_PERFORMANCE_TOKENS = {
    "future",
    "next_",
    "12m",
    "6m",
    "max_dpd",
    "max_observed",
    "first_90",
    "observed_mob",
}

DEFAULT_OUTCOME_TOKENS = {
    "default_date",
    "default_type",
    "dpd_at_default",
    "ead_at_default",
    "writeoff",
    "default_flag",
    "defaulted",
}

RECOVERY_OUTCOME_TOKENS = {
    "recovery",
    "recoveries",
    "recovered",
    "collection",
    "collection_cost",
}

LGD_EAD_OUTCOME_TOKENS = {
    "realized_lgd",
    "realized_ccf",
    "lgd_proxy",
    "ead_proxy",
    "ead_at_default",
}

DECISION_ENGINE_TOKENS = {
    "engine_",
    "decision_",
    "approved_",
    "offered_",
    "policy_version",
    "rule_hits",
}

SUSPICIOUS_NAME_TOKENS = {
    "target",
    "future",
    "recovered",
    "collection",
    "dpd_12m",
    "first_90",
    "max_dpd",
    "observed_mob",
}


def classify_leakage_column(column: str) -> tuple[str, str] | None:
    """Return leakage category and reason for a column, or None if it is allowed."""

    col = column.lower()

    if col in ID_COLUMNS or col.endswith("_id"):
        return "id", "Identifier columns are not model features."

    if col in TARGET_COLUMNS or col.startswith("target_") or "target" in col:
        return "target", "Target columns directly encode the modeling outcome."

    if any(token in col for token in DEFAULT_OUTCOME_TOKENS):
        return "default_outcome", "Default outcome fields are only known after the observation date."

    if any(token in col for token in RECOVERY_OUTCOME_TOKENS):
        return "recovery_outcome", "Recovery and collection fields are post-default outcomes."

    if any(token in col for token in LGD_EAD_OUTCOME_TOKENS):
        return "lgd_ead_outcome", "LGD/EAD realized outcome fields are not valid PD predictors."

    if any(token in col for token in DECISION_ENGINE_TOKENS):
        return "decision_engine_output", "Existing decision engine outputs are excluded from model features."

    if any(token in col for token in FUTURE_PERFORMANCE_TOKENS):
        return "future_performance", "Future performance fields can leak post-observation information."

    if col in DATE_COLUMNS or col.endswith("_date"):
        return "date", "Date columns are used for splitting or event timing, not directly as PD features."

    if any(token in col for token in SUSPICIOUS_NAME_TOKENS):
        return "suspicious_name_token", "Column name contains a token commonly linked to leakage."

    return None


def build_leakage_exclusion_report(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for column in df.columns:
        classification = classify_leakage_column(column)

        if classification is None:
            continue

        category, reason = classification

        rows.append(
            {
                "column": column,
                "reason": reason,
                "category": category,
            }
        )

    report = pd.DataFrame(rows, columns=["column", "reason", "category"])

    if report.empty:
        return report

    category_order = {
        "id": 1,
        "date": 2,
        "target": 3,
        "default_outcome": 4,
        "recovery_outcome": 5,
        "lgd_ead_outcome": 6,
        "decision_engine_output": 7,
        "future_performance": 8,
        "suspicious_name_token": 9,
    }

    report["_order"] = report["category"].map(category_order).fillna(99)
    report = report.sort_values(["_order", "column"]).drop(columns="_order").reset_index(drop=True)

    return report
