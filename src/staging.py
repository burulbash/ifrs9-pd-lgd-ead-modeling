from __future__ import annotations

import pandas as pd


RATING_ORDER = {
    "A": 1,
    "B": 2,
    "C": 3,
    "D": 4,
    "E": 5,
    "F": 6,
    "Default": 7,
}


def flag_is_true(value) -> bool:
    if pd.isna(value):
        return False

    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}

    return bool(value)


def rating_to_order(rating: str | None) -> int | None:
    if rating is None or pd.isna(rating):
        return None

    return RATING_ORDER.get(str(rating))


def calculate_rating_downgrade(
    origination_rating: str | None,
    current_rating: str | None,
) -> int | None:
    origination_order = rating_to_order(origination_rating)
    current_order = rating_to_order(current_rating)

    if origination_order is None or current_order is None:
        return None

    return current_order - origination_order


def assign_ifrs9_stage_for_row(row: pd.Series) -> tuple[int, str]:
    default_flag = flag_is_true(row.get("default_flag", 0))
    writeoff_flag = flag_is_true(row.get("writeoff_flag", 0))

    current_dpd = pd.to_numeric(row.get("current_dpd", 0), errors="coerce")
    dpd_at_default = pd.to_numeric(row.get("dpd_at_default", 0), errors="coerce")

    if pd.isna(current_dpd):
        current_dpd = 0
    if pd.isna(dpd_at_default):
        dpd_at_default = 0

    if default_flag or writeoff_flag or current_dpd >= 90 or dpd_at_default >= 90:
        return 3, "default_or_90dpd"

    watchlist_flag = flag_is_true(row.get("watchlist_flag", 0))
    restructuring_flag = flag_is_true(row.get("restructuring_flag", 0))

    pd_ratio = pd.to_numeric(row.get("pd_ratio_current_to_origination", None), errors="coerce")
    downgrade = pd.to_numeric(row.get("rating_downgrade_notches", None), errors="coerce")

    reasons = []

    if not pd.isna(downgrade) and downgrade >= 2:
        reasons.append("rating_downgrade_2plus")

    if not pd.isna(pd_ratio) and pd_ratio >= 2:
        reasons.append("pd_doubled")

    if current_dpd >= 30:
        reasons.append("30dpd")

    if watchlist_flag:
        reasons.append("watchlist")

    if restructuring_flag:
        reasons.append("restructuring")

    if reasons:
        return 2, "+".join(reasons)

    return 1, "performing"


def assign_ifrs9_stage(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()

    if "rating_downgrade_notches" not in data.columns:
        data["rating_downgrade_notches"] = data.apply(
            lambda row: calculate_rating_downgrade(
                row.get("origination_rating_grade"),
                row.get("current_rating_grade"),
            ),
            axis=1,
        )

    stage_results = data.apply(assign_ifrs9_stage_for_row, axis=1)

    data["ifrs9_stage"] = [result[0] for result in stage_results]
    data["ifrs9_stage_reason"] = [result[1] for result in stage_results]

    return data


def build_stage_distribution(df: pd.DataFrame) -> pd.DataFrame:
    distribution = (
        df.groupby("ifrs9_stage", as_index=False)
        .agg(
            facilities=("facility_id", "size"),
            total_outstanding=("outstanding_amount", "sum"),
            avg_current_pd=("current_pd_estimate", "mean"),
            avg_origination_pd=("origination_pd_estimate", "mean"),
            default_rate=("default_flag", "mean"),
        )
        .sort_values("ifrs9_stage")
    )

    total_facilities = distribution["facilities"].sum()
    total_outstanding = distribution["total_outstanding"].sum()

    distribution["facility_share"] = distribution["facilities"] / total_facilities
    distribution["outstanding_share"] = distribution["total_outstanding"] / total_outstanding

    return distribution


def build_stage_by_rating(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["current_rating_grade", "ifrs9_stage"], dropna=False, as_index=False)
        .agg(
            facilities=("facility_id", "size"),
            total_outstanding=("outstanding_amount", "sum"),
            avg_current_pd=("current_pd_estimate", "mean"),
            default_rate=("default_flag", "mean"),
        )
        .sort_values(["current_rating_grade", "ifrs9_stage"])
    )


def build_rating_migration_matrix(df: pd.DataFrame) -> pd.DataFrame:
    matrix = pd.crosstab(
        df["origination_rating_grade"],
        df["current_rating_grade"],
        dropna=False,
    )

    return matrix.reset_index()
