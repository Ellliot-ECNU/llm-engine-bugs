#!/usr/bin/env python3
"""Plot the monthly composition of the number of files changed per fix."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "monthly_file_bucket_counts.json"
OUTPUT_PNG = BASE_DIR / "figures" / "generated" / "monthly_file_bucket_trend.png"
OUTPUT_PDF = BASE_DIR / "figures" / "generated" / "monthly_file_bucket_trend.pdf"
SINGLE_COLUMN_PNG = BASE_DIR / "figures" / "generated" / "monthly_file_bucket_trend_single_column.png"
SINGLE_COLUMN_PDF = BASE_DIR / "figures" / "generated" / "monthly_file_bucket_trend_single_column.pdf"

START_MONTH = "2023-01"
BUCKETS = ("1 file", "2-5 files", "6+ files")
COLORS = ("#4C78A8", "#72B7B2", "#F2CF5B")


def plot_trend(months, shares, *, single_column: bool) -> None:
    if single_column:
        output_png = SINGLE_COLUMN_PNG
        output_pdf = SINGLE_COLUMN_PDF
        figsize = (3.5, 1.85)
        font_size = 9
        title_size = 10.5
        label_size = 10
        legend_size = 8.5
        tick_step = 8
    else:
        output_png = OUTPUT_PNG
        output_pdf = OUTPUT_PDF
        figsize = (16, 5.33)
        font_size = 11
        title_size = 15
        label_size = 12
        legend_size = 11
        tick_step = 4

    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Liberation Sans", "sans-serif"],
            "font.weight": "bold",
            "axes.labelweight": "bold",
            "axes.titleweight": "bold",
            "pdf.fonttype": 42,
            "font.size": font_size,
            "axes.titlesize": title_size,
            "axes.labelsize": label_size,
            "legend.fontsize": legend_size,
            "xtick.labelsize": font_size,
            "ytick.labelsize": font_size,
        }
    )

    fig, ax = plt.subplots(figsize=figsize)
    x = range(len(months))
    ax.stackplot(x, *shares, labels=BUCKETS, colors=COLORS, alpha=0.88)

    ax.set_ylabel("Share of fixes (%)")
    ax.set_ylim(0, 100)
    ax.set_yticks(range(0, 101, 20))

    tick_indices = list(range(0, len(months), tick_step))
    if not single_column and tick_indices[-1] != len(months) - 1:
        tick_indices.append(len(months) - 1)
    ax.set_xticks(tick_indices)
    ax.set_xticklabels([months[index] for index in tick_indices])
    plt.setp(ax.get_xticklabels(), fontfamily="Liberation Sans", fontweight="bold")
    plt.setp(ax.get_yticklabels(), fontfamily="Liberation Sans", fontweight="bold")

    legend = ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=len(BUCKETS),
        frameon=False,
    )
    plt.setp(legend.get_texts(), fontfamily="Liberation Sans", fontweight="bold")
    ax.grid(axis="y", color="#7f7f7f", linewidth=0.8, linestyle="--", alpha=0.70)
    ax.grid(axis="x", color="#7f7f7f", linewidth=0.8, linestyle="--", alpha=0.70)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.margins(x=0)

    fig.tight_layout()
    fig.savefig(output_png, dpi=300 if single_column else 200, bbox_inches="tight")
    fig.savefig(output_pdf, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {output_png}")
    print(f"Saved: {output_pdf}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--variant",
        choices=("both", "double", "single"),
        default="both",
        help="figure width to generate (default: both)",
    )
    args = parser.parse_args()

    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    months = [month for month in data["months"] if month >= START_MONTH]
    if not months:
        raise ValueError(f"No monthly data found on or after {START_MONTH}.")

    table = data["table"]
    shares = [
        [table[month][bucket]["percentage"] for month in months]
        for bucket in BUCKETS
    ]

    if args.variant in ("both", "double"):
        plot_trend(months, shares, single_column=False)
    if args.variant in ("both", "single"):
        plot_trend(months, shares, single_column=True)


if __name__ == "__main__":
    main()
