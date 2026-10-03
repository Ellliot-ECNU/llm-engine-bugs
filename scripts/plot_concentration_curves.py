#!/usr/bin/env python3
"""将文件级与函数级 bug 浓度曲线分别绘制为独立的论文风格 PDF。"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter


PROJECT_LABELS = {
    "ggml-org/llama.cpp": "llama.cpp",
    "vllm-project/vllm": "vLLM",
    "deepspeedai/DeepSpeed": "DeepSpeed",
    "mlc-ai/mlc-llm": "MLC-LLM",
    "NVIDIA/TensorRT-LLM": "TensorRT-LLM",
    "huggingface/text-generation-inference": "TGI",
}

# 同一项目在两张图中保持相同颜色、线型和 marker。
COLORS = ["#2f4f3e", "#d62728", "#355c9a", "#b05ab0", "#18aeb5", "#3b2528"]
MARKERS = ["*", "^", "o", "+", "v", "x"]
LINESTYLES = ["-", "-", "-", "-", "-", "-"]


def pareto_points(items: List[Dict[str, Any]], metric: str) -> Tuple[List[float], List[float]]:
    cleaned = []
    for item in items:
        try:
            value = float(item.get(metric, 0))
        except (TypeError, ValueError):
            value = 0.0
        if value > 0:
            cleaned.append(value)
    cleaned.sort(reverse=True)
    if not cleaned:
        return [], []
    total = sum(cleaned)
    xs = [0.0]
    ys = [0.0]
    cumulative = 0.0
    count = len(cleaned)
    for rank, value in enumerate(cleaned, 1):
        cumulative += value
        xs.append(rank / count)
        ys.append(cumulative / total)
    return xs, ys


def load_projects(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("projects", {}) or {}


def draw_panel(ax, projects: Dict[str, Any], entity: str, metric: str) -> None:
    for index, (repo, project) in enumerate(projects.items()):
        xs, ys = pareto_points(project.get("files", []), metric)
        if not xs:
            continue
        marker_step = max(1, (len(xs) - 1) // 55)
        ax.plot(
            xs,
            ys,
            label=PROJECT_LABELS.get(repo, repo.split("/")[-1]),
            color=COLORS[index % len(COLORS)],
            linestyle=LINESTYLES[index % len(LINESTYLES)],
            linewidth=2.2,
            marker=MARKERS[index % len(MARKERS)],
            markersize=4.5,
            markevery=marker_step,
            markeredgewidth=0.8,
            alpha=0.98,
        )

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ticks = [i / 10 for i in range(1, 11)]
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.xaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    ax.set_xlabel(f"Fraction of bug {entity}", fontsize=19.5, fontweight="bold", labelpad=7)
    ax.set_ylabel("Fraction of bugs", fontsize=19.5, fontweight="bold", labelpad=7)
    ax.tick_params(axis="both", labelsize=15, width=1.1, direction="in", top=True, right=True)
    for tick_label in [*ax.get_xticklabels(), *ax.get_yticklabels()]:
        tick_label.set_fontweight("bold")
    ax.grid(True, linestyle=(0, (2, 4)), linewidth=0.8, color="#777777", alpha=0.8)
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)
    legend = ax.legend(
        loc="lower right",
        fontsize=14.25,
        frameon=True,
        fancybox=False,
        framealpha=1.0,
        edgecolor="#333333",
        borderpad=0.45,
        handlelength=2.0,
        labelspacing=0.3,
        ncol=1,
    )
    for text in legend.get_texts():
        text.set_fontweight("bold")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--files-input", default="data/pareto/bug_file_distribution_weighted_alpha0.8_by_project.json")
    parser.add_argument("--functions-input", default="data/bug_function_distribution_weighted_alpha0.8_by_project.json")
    parser.add_argument("--metric", default="weighted_bug_sum", choices=["weighted_bug_sum", "raw_bug_count"])
    parser.add_argument(
        "--files-output",
        default="figures/generated/concentration_files.pdf",
    )
    parser.add_argument(
        "--functions-output",
        default="figures/generated/concentration_functions.pdf",
    )
    args = parser.parse_args()

    file_projects = load_projects(Path(args.files_input))
    function_projects = load_projects(Path(args.functions_input))

    # 使用文件数据的项目顺序，并让函数图严格复用该顺序。
    common_repos = [repo for repo in file_projects if repo in function_projects]
    file_projects = {repo: file_projects[repo] for repo in common_repos}
    function_projects = {repo: function_projects[repo] for repo in common_repos}

    plt.rcParams.update({"font.family": "DejaVu Serif"})
    outputs = [
        (Path(args.files_output), file_projects, "files"),
        (Path(args.functions_output), function_projects, "functions"),
    ]
    for output, projects, entity in outputs:
        fig, ax = plt.subplots(figsize=(6.4, 5.3))
        draw_panel(ax, projects, entity, args.metric)
        fig.subplots_adjust(left=0.14, right=0.98, top=0.98, bottom=0.14)
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print(f"PDF: {output}")


if __name__ == "__main__":
    main()
