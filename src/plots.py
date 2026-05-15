from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def set_plot_theme() -> None:
    sns.set_theme(
        context="notebook",
        style="whitegrid",
        font_scale=1.0,
    )


def save_bar_plot(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    output_path: str | Path,
    xlabel: str | None = None,
    ylabel: str | None = None,
    rotation: int = 0,
) -> None:
    set_plot_theme()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plot_df = df.copy()

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(
        data=plot_df,
        x=x_col,
        y=y_col,
        ax=ax,
        errorbar=None,
    )

    ax.set_title(title)
    ax.set_xlabel(xlabel or x_col)
    ax.set_ylabel(ylabel or y_col)
    ax.tick_params(axis="x", rotation=rotation)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def save_line_plot(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    output_path: str | Path,
    group_col: str | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
) -> None:
    set_plot_theme()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plot_df = df.copy()

    fig, ax = plt.subplots(figsize=(9, 5))

    if group_col is None:
        sns.lineplot(
            data=plot_df,
            x=x_col,
            y=y_col,
            marker="o",
            ax=ax,
        )
    else:
        sns.lineplot(
            data=plot_df,
            x=x_col,
            y=y_col,
            hue=group_col,
            marker="o",
            ax=ax,
        )

    ax.set_title(title)
    ax.set_xlabel(xlabel or x_col)
    ax.set_ylabel(ylabel or y_col)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def save_actual_vs_predicted_plot(
    df: pd.DataFrame,
    x_col: str,
    actual_col: str,
    predicted_col: str,
    title: str,
    output_path: str | Path,
    xlabel: str | None = None,
    ylabel: str | None = None,
) -> None:
    set_plot_theme()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plot_df = df.copy()

    long_df = plot_df[[x_col, actual_col, predicted_col]].melt(
        id_vars=x_col,
        value_vars=[actual_col, predicted_col],
        var_name="series",
        value_name="value",
    )

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.lineplot(
        data=long_df,
        x=x_col,
        y="value",
        hue="series",
        marker="o",
        ax=ax,
    )

    ax.set_title(title)
    ax.set_xlabel(xlabel or x_col)
    ax.set_ylabel(ylabel or "value")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def save_rating_calibration_confidence_plot(
    df: pd.DataFrame,
    output_path: str | Path,
    rating_col: str = "rating_grade",
    observed_col: str = "observed_default_rate",
    predicted_col: str = "avg_predicted_pd",
    lower_ci_col: str = "observed_default_rate_lower_ci",
    upper_ci_col: str = "observed_default_rate_upper_ci",
    title: str = "Rating calibration with confidence intervals",
) -> None:
    set_plot_theme()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plot_df = df.copy()

    rating_order = {
        "A": 1,
        "B": 2,
        "C": 3,
        "D": 4,
        "E": 5,
        "F": 6,
        "Default": 7,
    }

    plot_df["_rating_order"] = plot_df[rating_col].map(rating_order).fillna(99)
    plot_df = plot_df.sort_values("_rating_order").reset_index(drop=True)

    x_values = list(range(len(plot_df)))
    x_labels = plot_df[rating_col].astype(str).tolist()

    observed = pd.to_numeric(plot_df[observed_col], errors="coerce")
    predicted = pd.to_numeric(plot_df[predicted_col], errors="coerce")
    lower_ci = pd.to_numeric(plot_df[lower_ci_col], errors="coerce")
    upper_ci = pd.to_numeric(plot_df[upper_ci_col], errors="coerce")

    lower_error = (observed - lower_ci).clip(lower=0)
    upper_error = (upper_ci - observed).clip(lower=0)

    fig, ax = plt.subplots(figsize=(9, 5))

    ax.plot(
        x_values,
        predicted,
        marker="o",
        label="avg predicted PD",
    )

    ax.errorbar(
        x_values,
        observed,
        yerr=[lower_error, upper_error],
        fmt="o",
        capsize=4,
        label="observed default rate",
    )

    ax.set_title(title)
    ax.set_xlabel("Rating grade")
    ax.set_ylabel("Default rate / PD")
    ax.set_xticks(x_values)
    ax.set_xticklabels(x_labels)
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
