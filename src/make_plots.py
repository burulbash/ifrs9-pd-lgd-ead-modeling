from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import PLOTS_DIR, REPORTS_DIR  # noqa: E402
from src.plots import (  # noqa: E402
    save_actual_vs_predicted_plot,
    save_bar_plot,
    save_line_plot,
)


def read_report(filename: str) -> pd.DataFrame | None:
    path = REPORTS_DIR / filename

    if not path.exists():
        print(f"Skipping missing report: {path}")
        return None

    return pd.read_csv(path)


def make_pd_plots() -> None:
    metrics = read_report("pd_model_metrics.csv")
    if metrics is not None:
        oot = metrics[metrics["split"].eq("oot")].copy()
        if not oot.empty:
            save_bar_plot(
                oot.sort_values("roc_auc", ascending=False),
                x_col="model",
                y_col="roc_auc",
                title="PD model OOT ROC-AUC",
                output_path=PLOTS_DIR / "pd_model_oot_roc_auc.png",
                ylabel="ROC-AUC",
                rotation=20,
            )

    rating = read_report("pd_rating_grade_summary.csv")
    if rating is not None and not rating.empty:
        save_actual_vs_predicted_plot(
            rating,
            x_col="rating_grade",
            actual_col="observed_default_rate",
            predicted_col="avg_predicted_pd",
            title="PD calibration by rating grade",
            output_path=PLOTS_DIR / "pd_calibration_by_rating_grade.png",
            xlabel="Rating grade",
            ylabel="Default rate / PD",
        )


def make_lgd_plots() -> None:
    calibration = read_report("lgd_calibration_by_decile.csv")
    if calibration is not None and not calibration.empty:
        save_actual_vs_predicted_plot(
            calibration,
            x_col="lgd_decile",
            actual_col="avg_actual_lgd",
            predicted_col="avg_predicted_lgd",
            title="LGD actual vs predicted by decile",
            output_path=PLOTS_DIR / "lgd_actual_vs_predicted_decile.png",
            xlabel="LGD prediction decile",
            ylabel="LGD",
        )

    segment = read_report("lgd_by_segment.csv")
    if segment is not None and not segment.empty:
        collateral = segment[segment["segment_type"].eq("collateral_type")].copy()
        if not collateral.empty:
            save_bar_plot(
                collateral.sort_values("avg_actual_lgd", ascending=False),
                x_col="segment",
                y_col="avg_actual_lgd",
                title="Actual LGD by collateral type",
                output_path=PLOTS_DIR / "lgd_by_collateral_type.png",
                xlabel="Collateral type",
                ylabel="Average actual LGD",
                rotation=20,
            )


def make_ead_plots() -> None:
    calibration = read_report("ead_ccf_calibration_by_decile.csv")
    if calibration is not None and not calibration.empty:
        save_actual_vs_predicted_plot(
            calibration,
            x_col="ccf_decile",
            actual_col="avg_actual_ccf",
            predicted_col="avg_predicted_ccf",
            title="CCF actual vs predicted by decile",
            output_path=PLOTS_DIR / "ead_ccf_actual_vs_predicted_decile.png",
            xlabel="CCF prediction decile",
            ylabel="CCF",
        )

    by_product = read_report("ead_ccf_by_product.csv")
    if by_product is not None and not by_product.empty:
        save_bar_plot(
            by_product.sort_values("avg_actual_ccf", ascending=False),
            x_col="product_type",
            y_col="avg_actual_ccf",
            title="Actual CCF by product type",
            output_path=PLOTS_DIR / "ead_ccf_by_product_type.png",
            xlabel="Product type",
            ylabel="Average actual CCF",
            rotation=20,
        )


def make_ifrs9_plots() -> None:
    stage_distribution = read_report("ifrs9_stage_distribution.csv")
    if stage_distribution is not None and not stage_distribution.empty:
        save_bar_plot(
            stage_distribution,
            x_col="ifrs9_stage",
            y_col="facilities",
            title="IFRS 9 stage distribution",
            output_path=PLOTS_DIR / "ifrs9_stage_distribution.png",
            xlabel="IFRS 9 stage",
            ylabel="Facilities",
        )

    ecl_by_stage = read_report("ifrs9_ecl_by_stage.csv")
    if ecl_by_stage is not None and not ecl_by_stage.empty:
        save_bar_plot(
            ecl_by_stage,
            x_col="ifrs9_stage",
            y_col="total_ecl",
            title="ECL by IFRS 9 stage",
            output_path=PLOTS_DIR / "ifrs9_ecl_by_stage.png",
            xlabel="IFRS 9 stage",
            ylabel="Total ECL",
        )

    ecl_by_rating = read_report("ifrs9_ecl_by_rating.csv")
    if ecl_by_rating is not None and not ecl_by_rating.empty:
        save_bar_plot(
            ecl_by_rating,
            x_col="current_rating_grade",
            y_col="total_ecl",
            title="ECL by rating grade",
            output_path=PLOTS_DIR / "ifrs9_ecl_by_rating.png",
            xlabel="Rating grade",
            ylabel="Total ECL",
        )


def make_stress_plots() -> None:
    stress_summary = read_report("stress_scenario_summary.csv")
    if stress_summary is not None and not stress_summary.empty:
        save_bar_plot(
            stress_summary.sort_values("total_ecl", ascending=False),
            x_col="scenario",
            y_col="total_ecl",
            title="Stress scenario ECL comparison",
            output_path=PLOTS_DIR / "stress_scenario_ecl_comparison.png",
            xlabel="Scenario",
            ylabel="Total ECL",
            rotation=20,
        )

        save_bar_plot(
            stress_summary.sort_values("ecl_change_pct_vs_base", ascending=False),
            x_col="scenario",
            y_col="ecl_change_pct_vs_base",
            title="Stress scenario ECL change vs base",
            output_path=PLOTS_DIR / "stress_scenario_ecl_change_pct.png",
            xlabel="Scenario",
            ylabel="ECL change vs base",
            rotation=20,
        )


def make_validation_plots() -> None:
    psi = read_report("validation_psi_summary.csv")
    if psi is not None and not psi.empty:
        save_bar_plot(
            psi.head(10).sort_values("psi", ascending=True),
            x_col="feature",
            y_col="psi",
            title="Top PSI features",
            output_path=PLOTS_DIR / "validation_top_psi_features.png",
            xlabel="Feature",
            ylabel="PSI",
            rotation=35,
        )

    pd_backtesting = read_report("validation_pd_backtesting_by_rating.csv")
    if pd_backtesting is not None and not pd_backtesting.empty:
        save_actual_vs_predicted_plot(
            pd_backtesting,
            x_col="rating_grade",
            actual_col="observed_default_rate",
            predicted_col="avg_predicted_pd",
            title="Validation: PD backtesting by rating",
            output_path=PLOTS_DIR / "validation_pd_backtesting_by_rating.png",
            xlabel="Rating grade",
            ylabel="Default rate / PD",
        )


def main() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    make_pd_plots()
    make_lgd_plots()
    make_ead_plots()
    make_ifrs9_plots()
    make_stress_plots()
    make_validation_plots()

    print(f"Plots saved to: {PLOTS_DIR}")


if __name__ == "__main__":
    main()
