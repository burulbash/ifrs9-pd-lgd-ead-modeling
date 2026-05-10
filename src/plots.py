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
