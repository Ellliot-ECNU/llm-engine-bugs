#!/usr/bin/env python3
"""
根因分布及其与外显表现关系的可视化
生成多种图表来具象化根因分布规律和根因-症状关联
"""

import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Patch
try:
    import seaborn as sns
except ImportError as exc:
    raise SystemExit("seaborn is required; install dependencies with: python -m pip install -r requirements.txt") from exc
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
import warnings
import os
import re
import math
warnings.filterwarnings('ignore')

# Language configuration
LANGUAGE = "en"  # "en" or "zh"

# Text labels based on language
LABELS = {
    "en": {
        "root_cause_layer": "Root Cause Layer",
        "bug_symptom": "Bug Symptom",
        "weighted_bug_count": "Weighted Bug Count",
        "percentage": "Percentage (%)",
        "lift_value": "Lift Value (P(Layer|Symptom)/P(Layer))",
        "pie_title": "Root Cause Layer Distribution (Pie)",
        "bar_title": "Root Cause Layer Distribution (Bar)",
        "heatmap_title": "Root Cause Layer vs Symptom Heatmap",
        "heatmap_pct_title": "Root Cause Layer vs Symptom Heatmap (%)\nEach row sums to 100%",
        "lift_title": "Root Cause-Symptom Association Heatmap (Lift, Positive Only)\nLift > 1 means symptom is more likely from this layer",
        "lift_all_title": "Root Cause-Symptom Association Heatmap (Lift, All Values)\nRed=Lift>1 (positive) | Blue=Lift<1 (negative)",
        "lift_12_title": "Root Cause-Symptom Association Heatmap (Lift, Range 1-2)\nDarker color = higher lift (range 1.0-2.0, values >2.0 marked with *)",
        "top_title": "Top Root Cause-Symptom Associations (Top 15)\nHigher Lift = stronger association",
        "lift_label": "Lift Value",
        "loading_data": "Loading data: {}",
        "processed_records": "Processed {:,} valid records",
        "saved": "Saved: {}",
        "generating": "\nGenerating visualizations...",
        "done": "\nAll visualizations generated!",
        "error_file_not_found": "Error: Input file not found: {}",
        "no_association": "Lift=1 (No Association)",
    },
    "zh": {
        "root_cause_layer": "根因层次",
        "bug_symptom": "Bug症状",
        "weighted_bug_count": "加权Bug数量",
        "percentage": "百分比 (%)",
        "lift_value": "Lift值 (P(层次|症状)/P(层次))",
        "pie_title": "根因层次分布（饼图）",
        "bar_title": "根因层次分布（柱状图）",
        "heatmap_title": "根因层次与症状分布热力图",
        "heatmap_pct_title": "根因层次与症状分布热力图（百分比）\n每行总和为100%，表示该层次内各症状的占比",
        "lift_title": "根因层次与症状关联强度热力图（Lift值，仅显示正相关）\nLift > 1表示该症状更偏向该层次",
        "lift_all_title": "根因层次与症状关联强度热力图（Lift值，显示全部）\n红色=Lift>1（正相关，症状偏向该层次）| 蓝色=Lift<1（负相关，症状不太可能来自该层次）",
        "lift_12_title": "根因层次与症状关联强度热力图（Lift值，颜色范围1-2）\n颜色越深表示Lift值越高（范围1.0-2.0，>2.0的值标记*）",
        "top_title": "根因层次与症状最强关联（Top 15）\nLift值越高，表示该症状更偏向该层次",
        "lift_label": "Lift值",
        "loading_data": "正在加载数据: {}",
        "processed_records": "处理了 {:,} 条有效记录",
        "saved": "已保存: {}",
        "generating": "\n正在生成可视化图表...",
        "done": "\n所有可视化图表生成完成！",
        "error_file_not_found": "错误: 找不到输入文件 {}",
        "no_association": "Lift=1（无关联）",
    }
}

# 全局字体属性
chinese_font_prop = None

def setup_chinese_font():
    """Setup Chinese font for matplotlib"""
    global chinese_font_prop
    
    if LANGUAGE == "zh":
        font_candidates = [
            ('Microsoft YaHei', ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/msyhbd.ttc']),
            ('SimHei', ['C:/Windows/Fonts/simhei.ttf']),
            ('SimSun', ['C:/Windows/Fonts/simsun.ttc']),
        ]
        
        available_fonts = {f.name: f for f in fm.fontManager.ttflist}
        
        for font_name, font_paths in font_candidates:
            if font_name in available_fonts:
                try:
                    font_file = available_fonts[font_name].fname
                    chinese_font_prop = FontProperties(fname=font_file)
                    plt.rcParams['font.sans-serif'] = [font_name, 'DejaVu Sans']
                    plt.rcParams['axes.unicode_minus'] = False
                    return True
                except Exception as e:
                    pass
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        chinese_font_prop = FontProperties(fname=font_path)
                        plt.rcParams['font.sans-serif'] = [font_name, 'DejaVu Sans']
                        plt.rcParams['axes.unicode_minus'] = False
                        return True
                    except Exception as e:
                        pass
        
        plt.rcParams['axes.unicode_minus'] = False
        chinese_font_prop = None
        return False
    else:
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'sans-serif']
        chinese_font_prop = None
        return True

def safe_div(n: float, d: float) -> float:
    return n / d if d else 0.0

# Short name mappings for display labels
SYMPTOM_SHORT = {
    "Incorrect/Inaccuracy Output": "OutErr",
    "Build/Compilation Error": "BuildErr",
    "Runtime Crash": "RCrash",
    "Performance/Memory Issue": "PerfMem",
    "API/argument parsing Error": "APIErr",
    "Hardware/Backend Compatibility Issue": "Compat",
    "Model Loading Error": "LoadErr",
    "Distributed Parallelism/Sharding Bug": "DistErr",
    "Security Vulnerability": "SecVuln",
    "Other": "Other",
}

LAYER_SHORT = {
    "Operators/Backend": "OpKernel",
    "Hardware Adaptation": "HwAdapt",
    "Scheduler/Runtime": "Schedule",
    "Compiler/Optimization": "CompOpt",
    "Config/Entrypoint": "ConfigEntry",
    "Build/Release": "BuildRel",
    "Tests/Bench": "TestBench",
    "Docs": "Docs",
    "Other": "Other",
}

LAYER_ORDER = [
    "Operators/Backend",
    "Hardware Adaptation",
    "Scheduler/Runtime",
    "Compiler/Optimization",
    "Config/Entrypoint",
    "Build/Release",
    "Tests/Bench",
    "Docs",
]

def layer_from_path(file_path: str, function: str = "") -> str:
    """将文件路径映射到工程层次"""
    p = (file_path or "").lstrip("./")
    low = p.lower()
    fname = Path(p).name.lower()
    fn = (function or "").lower()

    # Docs first
    if low.startswith("docs/") or fname in {"readme.md", "readme.rst", "contributing.md"} or fname.endswith(".md"):
        return "Docs"

    # Tests / benchmarks
    if low.startswith("tests/") or low.startswith("test/") or "/tests/" in low or "/test/" in low:
        return "Tests/Bench"
    if fname.startswith("test_") or fname.endswith("_test.py") or fname.endswith("_test.cc") or fname.endswith("_test.cpp"):
        return "Tests/Bench"
    if "benchmark" in low or low.startswith("bench") or "/bench" in low:
        return "Tests/Bench"

    # Build / release / packaging
    if low.startswith(".github/") or "/.github/" in low:
        return "Build/Release"
    if fname in {"cmakelists.txt", "makefile", "dockerfile", "setup.py", "pyproject.toml"}:
        return "Build/Release"
    if fname.endswith(".nix") or fname in {"flake.nix"}:
        return "Build/Release"

    # Config / entrypoints / server
    if "entrypoints" in low or "api_server" in low or "/server" in low or "openai" in low:
        return "Config/Entrypoint"
    if "config" in low and low.endswith((".py", ".yaml", ".yml", ".json", ".toml")):
        return "Config/Entrypoint"
    if "arg" in low and low.endswith(".py"):
        return "Config/Entrypoint"

    # Hardware adaptation
    hardware_kw = ["cuda", "cudnn", "hip", "rocm", "vulkan", "metal", "tensorrt", "xpu", "hpu", "neuron", "opencl"]
    if any(k in low for k in hardware_kw) or any(k in fn for k in hardware_kw):
        return "Hardware Adaptation"

    # Compiler / optimization stack
    compiler_kw = ["triton", "cutlass", "tvm", "xla", "compiler", "jit", "kernel", "codegen", "fusion", "inductor"]
    if any(k in low for k in compiler_kw) or any(k in fn for k in compiler_kw):
        return "Compiler/Optimization"

    # Scheduler / runtime
    runtime_kw = ["scheduler", "engine", "runtime", "worker", "executor", "parallel", "shard", "pipeline", "ray"]
    if any(k in low for k in runtime_kw) or any(k in fn for k in runtime_kw):
        return "Scheduler/Runtime"

    # Operators / backend core compute code
    if low.startswith("ggml/") or low.startswith("src/") or "/csrc/" in low:
        return "Operators/Backend"
    if low.endswith((".cu", ".cuh", ".c", ".cc", ".cpp", ".h", ".hpp", ".m", ".mm")):
        return "Operators/Backend"

    # Python core modules
    if low.endswith(".py"):
        return "Scheduler/Runtime"

    return "Other"

def normalize_symptom(symptom: str) -> str:
    """标准化症状名称"""
    if not symptom:
        return "Other"
    
    if symptom.startswith("other:"):
        return "Other"
    
    main_symptoms = {
        "Incorrect/Inaccuracy Output",
        "Build/Compilation Error", 
        "Runtime Crash",
        "Performance/Memory Issue",
        "API/argument parsing Error",
        "Hardware/Backend Compatibility Issue",
        "Model Loading Error",
        "Distributed Parallelism/Sharding Bug",
        "Security Vulnerability",
        "Other",
    }
    
    if symptom == "Security vulnerability":
        return "Security Vulnerability"
    
    if symptom in main_symptoms:
        return symptom
    else:
        return "Other"

def load_and_process_data(json_file: str):
    """Load the 12,707-bug corpus using its stored architectural-layer labels.

    Each bug contributes a total weight of one, divided equally across its
    distinct architectural layers. ``Other`` symptoms and layers contribute to
    the probability denominators but are omitted from the displayed matrix.
    """
    print(LABELS[LANGUAGE]["loading_data"].format(json_file))
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    layer_weight = Counter()
    symptom_total = Counter()
    layer_by_symptom = defaultdict(Counter)
    
    included_records = 0
    
    for url, bug in data.items():
        if url == 'metadata':
            continue
        
        # 过滤条件
        if not (bug.get("status") == "fixed" and bug.get("pr_status") == "Merged"):
            continue
        if bug.get("is_bug_related") is not True:
            continue
        
        symptom = bug.get("symptom")
        if not symptom or symptom == "Feature Request":
            continue
        
        symptom = normalize_symptom(symptom)
        root_cause_layers = [
            item.get("layer")
            for item in bug.get("root_causes", [])
            if isinstance(item, dict) and item.get("layer")
        ]
        if not root_cause_layers:
            root_cause_layers = bug.get("root_cause_layers") or []
        if not isinstance(root_cause_layers, list) or len(root_cause_layers) == 0:
            continue

        # root_causes[].layer is the manually saved canonical assignment.
        # root_cause_layers is retained only as a fallback for legacy records.
        valid_layers = set(LAYER_SHORT)
        layers = []
        for layer in root_cause_layers:
            layer = layer or "Other"
            if layer not in valid_layers:
                layer = "Other"
            if layer not in layers:
                layers.append(layer)
        if not layers:
            continue

        included_records += 1
        symptom_total[symptom] += 1

        # Each bug contributes exactly 1/k to each distinct layer.
        w_each = 1.0 / len(layers)
        for layer in layers:
            layer_weight[layer] += w_each
            layer_by_symptom[symptom][layer] += w_each
    
    print(LABELS[LANGUAGE]["processed_records"].format(included_records))
    return layer_weight, symptom_total, layer_by_symptom

def create_layer_distribution_plot(layer_weight, output_file: str, pdf_file: str = None):
    """Create root cause layer distribution plot"""
    setup_chinese_font()
    
    # 准备数据
    total_weight = sum(layer_weight.values())
    layers = []
    weights = []
    percentages = []
    
    for layer in LAYER_ORDER:
        if layer in layer_weight:
            w = layer_weight[layer]
            layers.append(layer)
            weights.append(w)
            percentages.append(w / total_weight * 100)
    
    # 创建子图：饼图和柱状图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    
    # 饼图
    colors = plt.cm.Set3(np.linspace(0, 1, len(layers)))
    layer_short_labels = [LAYER_SHORT[l] for l in layers]
    wedges, texts, autotexts = ax1.pie(weights, labels=layer_short_labels, autopct='%1.1f%%',
                                       startangle=90, colors=colors,
                                       textprops={'fontsize': 18, 'fontproperties': chinese_font_prop})
    
    for autotext in autotexts:
        autotext.set_color('black')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(18)
    
    # 柱状图
    bars = ax2.barh(layer_short_labels, weights, color=colors, edgecolor='black', alpha=0.8)
    ax2.set_xlabel(LABELS[LANGUAGE]["weighted_bug_count"], fontsize=24, fontweight='bold', fontproperties=chinese_font_prop)
    # 在柱子上添加数值
    for i, (bar, w, pct) in enumerate(zip(bars, weights, percentages)):
        ax2.text(bar.get_width() + 50, bar.get_y() + bar.get_height()/2,
                f'{w:.1f} ({pct:.1f}%)', 
                ha='left', va='center', fontsize=18, fontweight='bold', fontproperties=chinese_font_prop)
    
    ax2.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    if pdf_file:
        plt.savefig(pdf_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(LABELS[LANGUAGE]["saved"].format(output_file))

def create_layer_symptom_heatmap(layer_weight, layer_by_symptom, output_file: str, pdf_file: str = None):
    """Create root cause layer vs symptom heatmap (absolute count)"""
    setup_chinese_font()
    
    # 定义症状顺序
    symptoms_list = [
        "Incorrect/Inaccuracy Output",
        "Build/Compilation Error",
        "Runtime Crash",
        "Performance/Memory Issue",
        "API/argument parsing Error",
        "Hardware/Backend Compatibility Issue",
        "Model Loading Error",
        "Distributed Parallelism/Sharding Bug",
        "Security Vulnerability",
    ]
    
    # 准备数据矩阵
    layers = [l for l in LAYER_ORDER if l in layer_weight]
    heatmap_data = np.zeros((len(layers), len(symptoms_list)))
    
    for i, layer in enumerate(layers):
        for j, symptom in enumerate(symptoms_list):
            heatmap_data[i, j] = layer_by_symptom[symptom].get(layer, 0.0)
    
    # 创建热力图
    plt.figure(figsize=(16, 10))
    ax = sns.heatmap(heatmap_data, 
                     annot=False,
                     fmt='.1f',
                     cmap='YlOrRd',
                     xticklabels=[SYMPTOM_SHORT[s] for s in symptoms_list],
                     yticklabels=[LAYER_SHORT[l] for l in layers],
                     cbar_kws={'label': LABELS[LANGUAGE]["weighted_bug_count"]},
                     linewidths=0.5,
                     linecolor='gray',
                     vmin=0,
                     vmax=heatmap_data.max(),
                     square=False,
                     cbar=True)
    
    # 手动添加文本标注
    for i in range(len(layers)):
        for j in range(len(symptoms_list)):
            value = heatmap_data[i, j]
            if value > 0:
                threshold = heatmap_data.max() * 0.4
                text_color = 'white' if value > threshold else 'black'
                ax.text(j + 0.5, i + 0.5, f'{value:.1f}',
                       ha='center', va='center',
                       fontsize=20, fontweight='bold', color=text_color, fontproperties=chinese_font_prop)
    
    plt.xticks(rotation=0, ha='center', fontsize=22)
    plt.yticks(rotation=0, fontsize=22)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    if pdf_file:
        plt.savefig(pdf_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(LABELS[LANGUAGE]["saved"].format(output_file))

def create_layer_symptom_heatmap_percentage(layer_weight, layer_by_symptom, output_file: str, pdf_file: str = None):
    """Create root cause layer vs symptom heatmap (percentage, row-normalized)"""
    setup_chinese_font()
    
    # 定义症状顺序
    symptoms_list = [
        "Incorrect/Inaccuracy Output",
        "Build/Compilation Error",
        "Runtime Crash",
        "Performance/Memory Issue",
        "API/argument parsing Error",
        "Hardware/Backend Compatibility Issue",
        "Model Loading Error",
        "Distributed Parallelism/Sharding Bug",
        "Security Vulnerability",
    ]
    
    # 准备数据矩阵
    layers = [l for l in LAYER_ORDER if l in layer_weight]
    heatmap_data = np.zeros((len(layers), len(symptoms_list)))
    
    for i, layer in enumerate(layers):
        for j, symptom in enumerate(symptoms_list):
            heatmap_data[i, j] = layer_by_symptom[symptom].get(layer, 0.0)
    
    # 计算行百分比（每个层次内各症状的占比）
    row_sums = heatmap_data.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1  # 避免除零
    percentage_data = (heatmap_data / row_sums * 100)
    
    # 创建热力图
    plt.figure(figsize=(16, 10))
    ax = sns.heatmap(percentage_data, 
                     annot=False,
                     fmt='.1f',
                     cmap='YlOrRd',
                     xticklabels=[SYMPTOM_SHORT[s] for s in symptoms_list],
                     yticklabels=[LAYER_SHORT[l] for l in layers],
                     cbar_kws={'label': LABELS[LANGUAGE]["percentage"]},
                     linewidths=0.5,
                     linecolor='gray',
                     vmin=0,
                     vmax=100,
                     square=False,
                     cbar=True)
    
    # 手动添加文本标注（显示百分比）
    for i in range(len(layers)):
        for j in range(len(symptoms_list)):
            percentage = percentage_data[i, j]
            if percentage > 0:  # 只显示非零值
                threshold = 40  # 百分比阈值，用于判断文字颜色
                text_color = 'white' if percentage > threshold else 'black'
                ax.text(j + 0.5, i + 0.5, f'{percentage:.1f}%',
                       ha='center', va='center',
                       fontsize=20, fontweight='bold', color=text_color, fontproperties=chinese_font_prop)
    
    plt.xticks(rotation=0, ha='center', fontsize=22)
    plt.yticks(rotation=0, fontsize=22)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    if pdf_file:
        plt.savefig(pdf_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(LABELS[LANGUAGE]["saved"].format(output_file))

def create_layer_symptom_stacked_percentage(layer_weight, layer_by_symptom, output_file: str, pdf_file: str = None):
    """Create a 100% stacked bar chart of symptoms within each root-cause layer."""
    setup_chinese_font()
    if LANGUAGE == "en":
        plt.rcParams.update({
            'font.family': 'sans-serif',
            'font.sans-serif': ['Liberation Sans', 'sans-serif'],
            'font.weight': 'bold',
            'axes.labelweight': 'bold',
            'pdf.fonttype': 42,
        })

    symptoms_list = [
        "Incorrect/Inaccuracy Output",
        "Build/Compilation Error",
        "Runtime Crash",
        "Performance/Memory Issue",
        "API/argument parsing Error",
        "Hardware/Backend Compatibility Issue",
        "Model Loading Error",
        "Distributed Parallelism/Sharding Bug",
        "Security Vulnerability",
        "Other",
    ]
    layers = [layer for layer in LAYER_ORDER if layer in layer_weight]

    counts = np.array([
        [layer_by_symptom[symptom].get(layer, 0.0) for symptom in symptoms_list]
        for layer in layers
    ], dtype=float)
    # Normalize by the complete weight of each architectural layer.  Keeping
    # ``Other`` in the stack ensures that every bar represents the full symptom
    # distribution for that layer rather than a renormalized subset.
    row_totals = np.array([[layer_weight[layer]] for layer in layers], dtype=float)
    percentages = np.divide(
        counts * 100.0,
        row_totals,
        out=np.zeros_like(counts),
        where=row_totals != 0,
    )

    colors = [
        "#4C78A8", "#F58518", "#E45756", "#72B7B2", "#54A24B",
        "#B279A2", "#FF9DA6", "#9D755D", "#BAB0AC", "#6F6F6F",
    ]

    # Compact canvas and oversized typography are intentional: this figure is
    # designed to remain readable after being scaled to a single paper column.
    fig, ax = plt.subplots(figsize=(14, 7.5))
    x = np.arange(len(layers))
    annotations = []

    # Sort each root-cause layer independently: the largest symptom segment is
    # placed at the bottom and progressively smaller segments are stacked above.
    for layer_index, layer_x in enumerate(x):
        bottom = 0.0
        sorted_symptoms = sorted(
            range(len(symptoms_list)),
            key=lambda symptom_index: percentages[layer_index, symptom_index],
            reverse=True,
        )
        for symptom_index in sorted_symptoms:
            value = percentages[layer_index, symptom_index]
            if value <= 0:
                continue
            color = colors[symptom_index]
            bar = ax.bar(
                layer_x,
                value,
                bottom=bottom,
                width=0.88,
                color=color,
                edgecolor="white",
                linewidth=0.6,
            )[0]

            red, green, blue = matplotlib.colors.to_rgb(color)
            luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
            text_color = "black" if luminance > 0.58 else "white"
            if value >= 10.0:
                annotations.append((
                    bar.get_x() + bar.get_width() / 2,
                    bottom + value / 2,
                    value,
                    text_color,
                ))
            bottom += value

    # Draw labels after every segment so later bars cannot cover large text.
    for text_x, text_y, value, text_color in annotations:
        ax.text(
            text_x,
            text_y,
            f"{value:.0f}%",
            ha="center",
            va="center",
            fontsize=20,
            fontweight="bold",
            color=text_color,
            fontproperties=chinese_font_prop,
            zorder=5,
        )

    ax.set_ylim(0, 100)
    ax.set_yticks([0, 100])
    ax.set_yticklabels(
        ["0%", "100%"],
        fontsize=25,
        fontweight="bold",
        fontproperties=chinese_font_prop,
    )
    if LANGUAGE == "en":
        plt.setp(ax.get_yticklabels(), fontsize=25, fontfamily="Liberation Sans", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(
        [LAYER_SHORT[layer] for layer in layers],
        rotation=45,
        ha="right",
        fontsize=24,
        fontweight="bold",
        fontproperties=chinese_font_prop,
    )
    if LANGUAGE == "en":
        plt.setp(ax.get_xticklabels(), fontsize=24, fontfamily="Liberation Sans", fontweight="bold")
    ax.set_ylabel("")
    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    legend_handles = [
        Patch(facecolor=color, edgecolor="white", label=SYMPTOM_SHORT[symptom])
        for symptom, color in zip(symptoms_list, colors)
    ]
    legend = ax.legend(
        handles=legend_handles,
        title="Bug symptom",
        bbox_to_anchor=(1.01, 1.0),
        loc="upper left",
        frameon=False,
        borderaxespad=0.0,
        fontsize=18,
        title_fontsize=20,
        handlelength=0.75,
        handleheight=0.75,
        handletextpad=0.4,
        labelspacing=1.28,
        borderpad=0.1,
    )
    if legend:
        for legend_text in legend.get_texts():
            if chinese_font_prop is not None:
                legend_text.set_fontproperties(chinese_font_prop)
            legend_text.set_fontfamily("Liberation Sans" if LANGUAGE == "en" else legend_text.get_fontfamily())
            legend_text.set_fontsize(18)
            legend_text.set_fontweight("bold")
        if chinese_font_prop is not None:
            legend.get_title().set_fontproperties(chinese_font_prop)
        legend.get_title().set_fontfamily("Liberation Sans" if LANGUAGE == "en" else legend.get_title().get_fontfamily())
        legend.get_title().set_fontsize(20)
        legend.get_title().set_fontweight("bold")

    fig.tight_layout()
    fig.savefig(output_file, dpi=300, bbox_inches="tight", facecolor="white")
    if pdf_file:
        fig.savefig(pdf_file, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(LABELS[LANGUAGE]["saved"].format(output_file))

def calculate_lift_data(layer_weight, layer_by_symptom):
    """计算lift数据矩阵（公共函数）"""
    symptoms_list = [
        "Incorrect/Inaccuracy Output",
        "Build/Compilation Error",
        "Runtime Crash",
        "Performance/Memory Issue",
        "API/argument parsing Error",
        "Hardware/Backend Compatibility Issue",
        "Model Loading Error",
        "Distributed Parallelism/Sharding Bug",
        "Security Vulnerability",
    ]
    
    # 计算基础概率
    total_weight = sum(layer_weight.values())
    layer_base = {layer: safe_div(layer_weight[layer], total_weight) for layer in LAYER_ORDER if layer in layer_weight}
    
    # 准备数据矩阵
    layers = [l for l in LAYER_ORDER if l in layer_weight]
    lift_data = np.zeros((len(layers), len(symptoms_list)))
    
    for i, layer in enumerate(layers):
        for j, symptom in enumerate(symptoms_list):
            s_total_w = sum(layer_by_symptom[symptom].values()) or 0.0
            if s_total_w > 0:
                p_ls = safe_div(layer_by_symptom[symptom].get(layer, 0.0), s_total_w)
                p_l = layer_base.get(layer, 0.0)
                lift = safe_div(p_ls, p_l) if p_l > 0 else 0.0
                lift_data[i, j] = lift
    
    return lift_data, layers, symptoms_list

def create_lift_heatmap(layer_weight, layer_by_symptom, output_file: str, pdf_file: str = None):
    """Create lift heatmap (only showing lift >= 1)"""
    setup_chinese_font()
    
    lift_data, layers, symptoms_list = calculate_lift_data(layer_weight, layer_by_symptom)
    
    # 创建热力图
    plt.figure(figsize=(16, 10))
    
    # 使用mask隐藏lift < 1的值（表示负相关）
    mask = lift_data < 1.0
    
    ax = sns.heatmap(lift_data, 
                     annot=False,
                     fmt='.2f',
                     cmap='YlOrRd',
                     xticklabels=[SYMPTOM_SHORT[s] for s in symptoms_list],
                     yticklabels=[LAYER_SHORT[l] for l in layers],
                     linewidths=0.5,
                     linecolor='gray',
                     vmin=0,
                     vmax=lift_data.max(),
                     square=False,
                     cbar=True,
                     mask=mask)
    
    # 手动添加文本标注（只显示lift >= 1的值）
    for i in range(len(layers)):
        for j in range(len(symptoms_list)):
            lift = lift_data[i, j]
            if lift >= 1.0:  # 只显示正相关的lift值
                text_color = 'white' if lift > lift_data.max() * 0.6 else 'black'
                ax.text(j + 0.5, i + 0.5, f'{lift:.2f}',
                       ha='center', va='center',
                       fontsize=20, fontweight='bold', color=text_color, fontproperties=chinese_font_prop)
    
    plt.xticks(rotation=0, ha='center', fontsize=22)
    plt.yticks(rotation=0, fontsize=22)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    if pdf_file:
        plt.savefig(pdf_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(LABELS[LANGUAGE]["saved"].format(output_file))

def create_lift_heatmap_all(layer_weight, layer_by_symptom, output_file: str, pdf_file: str = None):
    """Create lift heatmap (showing all lift values)"""
    setup_chinese_font()
    
    lift_data, layers, symptoms_list = calculate_lift_data(layer_weight, layer_by_symptom)
    
    # 创建热力图
    plt.figure(figsize=(16, 10))
    
    # 计算合适的vmin和vmax，确保1.0在中心
    max_lift = lift_data.max()
    min_lift = lift_data[lift_data > 0].min() if np.any(lift_data > 0) else 0.1
    # 确保对称范围，以1.0为中心
    vmin = min(0.5, min_lift)  # 至少显示到0.5
    vmax = max(2.0, max_lift)  # 至少显示到2.0
    
    # 使用diverging colormap
    ax = sns.heatmap(lift_data, 
                     annot=False,
                     fmt='.2f',
                     cmap='RdBu_r',
                     xticklabels=[SYMPTOM_SHORT[s] for s in symptoms_list],
                     yticklabels=[LAYER_SHORT[l] for l in layers],
                     cbar_kws={'label': LABELS[LANGUAGE]["lift_value"]},
                     linewidths=0.5,
                     linecolor='gray',
                     vmin=vmin,
                     vmax=vmax,
                     center=1.0,
                     square=False,
                     cbar=True)
    
    # 手动添加文本标注（显示所有非零值）
    for i in range(len(layers)):
        for j in range(len(symptoms_list)):
            lift = lift_data[i, j]
            if lift > 0:  # 显示所有非零值
                # 根据lift值判断文字颜色
                if lift >= 1.0:
                    # 正相关：深色背景用白色字，浅色背景用黑色字
                    text_color = 'white' if lift > 1.5 else 'black'
                else:
                    # 负相关：浅色背景用黑色字
                    text_color = 'black'
                
                ax.text(j + 0.5, i + 0.5, f'{lift:.2f}',
                       ha='center', va='center',
                       fontsize=20, fontweight='bold', color=text_color, fontproperties=chinese_font_prop)
    
    plt.xticks(rotation=0, ha='center', fontsize=22)
    plt.yticks(rotation=0, fontsize=22)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    if pdf_file:
        plt.savefig(pdf_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(LABELS[LANGUAGE]["saved"].format(output_file))

def create_lift_heatmap_range_1_2(layer_weight, layer_by_symptom, output_file: str, pdf_file: str = None):
    """Create lift heatmap (color range 1-2)"""
    setup_chinese_font()
    if LANGUAGE == "en":
        plt.rcParams.update({
            'font.family': 'sans-serif',
            'font.sans-serif': ['Liberation Sans', 'sans-serif'],
            'font.weight': 'bold',
            'axes.labelweight': 'bold',
            'pdf.fonttype': 42,
        })
    
    lift_data, layers, symptoms_list = calculate_lift_data(layer_weight, layer_by_symptom)
    
    # 创建热力图；加宽画布，避免放大后的横坐标标签互相覆盖。
    plt.figure(figsize=(19, 10))
    
    # 固定颜色范围在1-2
    vmin = 1.0
    vmax = 2.0
    
    # 使用sequential colormap（从1到2的渐变色）
    ax = plt.gca()
    ax.pcolormesh(
        lift_data,
        cmap='YlOrRd',
        vmin=vmin,
        vmax=vmax,
        edgecolors='gray',
        linewidth=0.5,
        shading='flat',
    )
    ax.set_xlim(0, len(symptoms_list))
    ax.set_ylim(len(layers), 0)
    ax.set_xticks(np.arange(len(symptoms_list)) + 0.5)
    ax.set_yticks(np.arange(len(layers)) + 0.5)
    ax.set_xticklabels([SYMPTOM_SHORT[s] for s in symptoms_list])
    ax.set_yticklabels([LAYER_SHORT[l] for l in layers])

    ax.set_xlabel(LABELS[LANGUAGE]["bug_symptom"], fontsize=28, fontweight='bold',
                  fontproperties=chinese_font_prop)
    ax.set_ylabel("Architectural Layers" if LANGUAGE == "en" else "架构层次",
                  fontsize=28, fontweight='bold', fontproperties=chinese_font_prop)
    
    # 手动添加文本标注
    for i in range(len(layers)):
        for j in range(len(symptoms_list)):
            lift = lift_data[i, j]
            if lift >= 1.0:  # 只显示正相关的值
                if lift <= 2.0:
                    # 1-2范围内的值：根据lift值判断文字颜色
                    text_color = 'white' if lift > 1.6 else 'black'
                    ax.text(j + 0.5, i + 0.5, f'{lift:.2f}',
                           ha='center', va='center',
                           fontsize=24, fontweight='bold', color=text_color, fontproperties=chinese_font_prop)
                else:
                    # >2的值：显示数值，添加星号标记表示超出范围
                    text_color = 'white'  # 最深红色背景用白色字
                    ax.text(j + 0.5, i + 0.5, f'{lift:.2f}*',
                           ha='center', va='center',
                           fontsize=24, fontweight='bold', color=text_color, fontproperties=chinese_font_prop)
    
    plt.xticks(rotation=0, ha='center', fontsize=26)
    plt.yticks(rotation=0, fontsize=26)
    plt.setp(ax.get_xticklabels(), fontweight='bold')
    plt.setp(ax.get_yticklabels(), fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    if pdf_file:
        plt.savefig(pdf_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(LABELS[LANGUAGE]["saved"].format(output_file))

def create_top_associations_plot(layer_weight, layer_by_symptom, output_file: str, pdf_file: str = None):
    """Create top associations bar chart"""
    setup_chinese_font()
    
    # 计算所有lift值
    total_weight = sum(layer_weight.values())
    layer_base = {layer: safe_div(layer_weight[layer], total_weight) for layer in LAYER_ORDER if layer in layer_weight}
    
    associations = []
    
    symptoms_list = [
        "Incorrect/Inaccuracy Output",
        "Build/Compilation Error",
        "Runtime Crash",
        "Performance/Memory Issue",
        "API/argument parsing Error",
        "Hardware/Backend Compatibility Issue",
        "Model Loading Error",
        "Distributed Parallelism/Sharding Bug",
        "Security Vulnerability",
    ]
    
    for symptom in symptoms_list:
        s_total_w = sum(layer_by_symptom[symptom].values()) or 0.0
        if s_total_w <= 0:
            continue
        for layer in LAYER_ORDER:
            if layer not in layer_weight:
                continue
            p_ls = safe_div(layer_by_symptom[symptom].get(layer, 0.0), s_total_w)
            p_l = layer_base.get(layer, 0.0)
            lift = safe_div(p_ls, p_l) if p_l > 0 else 0.0
            if lift >= 1.25:  # 只保留显著关联
                associations.append({
                    'symptom': symptom,
                    'layer': layer,
                    'lift': lift
                })
    
    # 按lift值排序，取Top 15
    associations.sort(key=lambda x: x['lift'], reverse=True)
    top_associations = associations[:15]
    
    # 创建条形图
    fig, ax = plt.subplots(figsize=(14, 10))
    
    labels = [f"{SYMPTOM_SHORT[a['symptom']]} × {LAYER_SHORT[a['layer']]}" for a in top_associations]
    lifts = [a['lift'] for a in top_associations]
    
    bars = ax.barh(range(len(labels)), lifts, color=plt.cm.viridis(np.linspace(0, 1, len(labels))))
    
    # 添加数值标签
    for i, (bar, lift) in enumerate(zip(bars, lifts)):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                f'{lift:.2f}', ha='left', va='center', 
                fontsize=20, fontweight='bold', fontproperties=chinese_font_prop)
    
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=18, fontproperties=chinese_font_prop)
    ax.set_xlabel(LABELS[LANGUAGE]["lift_label"], fontsize=24, fontweight='bold', fontproperties=chinese_font_prop)
    ax.axvline(x=1.0, color='red', linestyle='--', linewidth=1, alpha=0.5, label=LABELS[LANGUAGE]["no_association"])
    legend = ax.legend(prop=chinese_font_prop)
    if legend:
        for text in legend.get_texts():
            text.set_fontproperties(chinese_font_prop)
    ax.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    if pdf_file:
        plt.savefig(pdf_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(LABELS[LANGUAGE]["saved"].format(output_file))

def main():
    """Main function"""
    setup_chinese_font()
    
    # 文件路径
    input_file = Path('data/final_bug_results_with_root_cause_completed_symptom.json')
    output_dir = Path('figures') / 'generated' / 'rq1_symptom_layer'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_file.exists():
        print(LABELS[LANGUAGE]["error_file_not_found"].format(input_file))
        return
    
    # 加载和处理数据
    layer_weight, symptom_total, layer_by_symptom = load_and_process_data(str(input_file))
    
    # 创建各种可视化图表
    print(LABELS[LANGUAGE]["generating"])
    
    # Helper to derive pdf path from png path
    def pdf_of(png_path):
        return str(png_path).replace('.png', '.pdf')
    
    # 1. 根因层次分布图
    p1 = str(output_dir / 'root_cause_layer_distribution.png')
    create_layer_distribution_plot(layer_weight, p1, pdf_of(p1))
    
    # 2. 根因层次与症状热力图（绝对数量）
    p2 = str(output_dir / 'root_cause_symptom_heatmap.png')
    create_layer_symptom_heatmap(layer_weight, layer_by_symptom, p2, pdf_of(p2))
    
    # 2b. 根因层次与症状热力图（百分比形式）
    p3 = str(output_dir / 'root_cause_symptom_heatmap_percentage.png')
    create_layer_symptom_heatmap_percentage(layer_weight, layer_by_symptom, p3, pdf_of(p3))
    
    # 2c. Percentage distribution as a 100% stacked bar chart.
    p3b = str(output_dir / 'root_cause_symptom_stacked_percentage.png')
    create_layer_symptom_stacked_percentage(layer_weight, layer_by_symptom, p3b, pdf_of(p3b))
    # 3. Lift值热力图（关联强度）- 只显示lift>=1的版本
    p4 = str(output_dir / 'root_cause_symptom_lift_heatmap.png')
    create_lift_heatmap(layer_weight, layer_by_symptom, p4, pdf_of(p4))
    
    # 3b. Lift值热力图（显示所有lift值）
    p5 = str(output_dir / 'root_cause_symptom_lift_heatmap_all.png')
    create_lift_heatmap_all(layer_weight, layer_by_symptom, p5, pdf_of(p5))
    
    # 3c. Lift值热力图（颜色范围限制在1-2）
    p6 = str(output_dir / 'root_cause_symptom_lift_heatmap_range_1_2.png')
    create_lift_heatmap_range_1_2(layer_weight, layer_by_symptom, p6, pdf_of(p6))
    
    # 4. 最强关联条形图
    p7 = str(output_dir / 'root_cause_symptom_top_associations.png')
    create_top_associations_plot(layer_weight, layer_by_symptom, p7, pdf_of(p7))
    
    print(LABELS[LANGUAGE]["done"])

if __name__ == '__main__':
    main()
