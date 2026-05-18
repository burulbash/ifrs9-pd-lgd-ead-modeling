from __future__ import annotations

import pandas as pd


RATING_ORDER = {
    "A": 1,
    "B": 2,
    "C": 3,
    "D": 4,
    "E": 5,
    "F": 6,
}


def build_alternative_rating_mapping(
    rating_summary: pd.DataFrame,
    min_bucket_size: int = 50,
) -> pd.DataFrame:
    data = rating_summary.copy()

    required = {
        "rating_grade",
        "facilities",
        "observed_defaults",
        "observed_default_rate",
        "avg_predicted_pd",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data["rating_order"] = data["rating_grade"].map(RATING_ORDER).fillna(99)
    data = data.sort_values("rating_order").reset_index(drop=True)

    rows = []

    for _, row in data.iterrows():
        original_grade = row["rating_grade"]
        original_facilities = int(row["facilities"])

        alternative_grade = original_grade
        rule = "unchanged"

        if original_grade == "F" and original_facilities < min_bucket_size:
            alternative_grade = "E_F"
            rule = "merge sparse F into E/F bucket"
        elif original_grade == "E":
            f_row = data[data["rating_grade"].eq("F")]
            if not f_row.empty and int(f_row["facilities"].iloc[0]) < min_bucket_size:
                alternative_grade = "E_F"
                rule = "merge E with sparse F bucket"

        rows.append(
            {
                "original_rating_grade": original_grade,
                "alternative_rating_grade": alternative_grade,
                "rule": rule,
                "original_facilities": original_facilities,
                "original_observed_defaults": int(row["observed_defaults"]),
                "original_observed_default_rate": float(row["observed_default_rate"]),
                "original_avg_predicted_pd": float(row["avg_predicted_pd"]),
            }
        )

    return pd.DataFrame(rows)


def build_alternative_rating_backtesting(
    rating_summary: pd.DataFrame,
    mapping: pd.DataFrame,
) -> pd.DataFrame:
    data = rating_summary.copy()

    data = data.merge(
        mapping[["original_rating_grade", "alternative_rating_grade"]],
        left_on="rating_grade",
        right_on="original_rating_grade",
        how="left",
    )

    data["alternative_rating_grade"] = data["alternative_rating_grade"].fillna(data["rating_grade"])
    data["weighted_predicted_defaults"] = data["facilities"] * data["avg_predicted_pd"]

    grouped = (
        data.groupby("alternative_rating_grade", as_index=False)
        .agg(
            facilities=("facilities", "sum"),
            observed_defaults=("observed_defaults", "sum"),
            expected_defaults=("weighted_predicted_defaults", "sum"),
            min_predicted_pd=("min_predicted_pd", "min"),
            max_predicted_pd=("max_predicted_pd", "max"),
        )
    )

    grouped["observed_default_rate"] = grouped["observed_defaults"] / grouped["facilities"]
    grouped["avg_predicted_pd"] = grouped["expected_defaults"] / grouped["facilities"]
    grouped["calibration_error"] = grouped["avg_predicted_pd"] - grouped["observed_default_rate"]

    order = {
        "A": 1,
        "B": 2,
        "C": 3,
        "D": 4,
        "E": 5,
        "E_F": 6,
        "F": 7,
    }
    grouped["_order"] = grouped["alternative_rating_grade"].map(order).fillna(99)

    return (
        grouped.sort_values("_order")
        .drop(columns="_order")
        .reset_index(drop=True)
    )
