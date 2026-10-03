#!/usr/bin/env python3
"""Generate the public, canonical RQ1--RQ3 summaries and reports.

The release repository intentionally excludes complete upstream patches.  This
script regenerates every aggregate that can be derived from the public export
and records the remaining patch-derived statistics from the published derived
data files.  Use ``--check`` to verify that checked-in reports are current.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
REPORTS = ROOT / "reports"

BUGS_PATH = DATA / "final_bug_results_with_root_cause_completed_symptom.json"
OPERATIONS_PATH = DATA / "final_bug_results_with_root_cause_completed_symptom_fixed_merged_fix_pattern.json"
FILE_DISTRIBUTION_PATH = DATA / "pareto/bug_file_distribution_weighted_alpha0.8_by_project.json"
FUNCTION_DISTRIBUTION_PATH = DATA / "bug_function_distribution_weighted_alpha0.8_by_project.json"
FIX_SIZE_PATH = DATA / "fix_size_stats.json"
FILE_BREADTH_PATH = DATA / "monthly_file_bucket_counts.json"
RQ3_LAYER_PATH = RESULTS / "rq3_layer_trends/rq3_layer_trend_results.json"

PROJECT_LABELS = {
    "ggml-org/llama.cpp": "llama.cpp",
    "vllm-project/vllm": "vLLM",
    "deepspeedai/DeepSpeed": "DeepSpeed",
    "mlc-ai/mlc-llm": "MLC-LLM",
    "NVIDIA/TensorRT-LLM": "TensorRT-LLM",
    "huggingface/text-generation-inference": "TGI",
}
PROJECT_ORDER = ("llama.cpp", "vLLM", "DeepSpeed", "MLC-LLM", "TensorRT-LLM", "TGI")
SYMPTOM_ORDER = (
    "API/argument parsing Error",
    "Incorrect/Inaccuracy Output",
    "Performance/Memory Issue",
    "Build/Compilation Error",
    "Hardware/Backend Compatibility Issue",
    "Runtime Crash",
    "Model Loading Error",
    "Distributed Parallelism/Sharding Bug",
    "Other",
    "Security Vulnerability",
)
LAYER_ORDER = (
    "Scheduler/Runtime",
    "Hardware Adaptation",
    "Operators/Backend",
    "Config/Entrypoint",
    "Tests/Bench",
    "Other",
    "Compiler/Optimization",
    "Build/Release",
    "Docs",
)
MAJOR_OPERATIONS = (
    "Correction",
    "Adaptation",
    "Configuration",
    "Validation",
    "Reorganization",
    "Recovery",
    "Optimization",
    "Synchronization",
    "Allocation",
)
DISPLAY_OPERATION = {"Correction": "Logic Correction"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if checked-in reports or summaries differ from regenerated content",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_from_url(url: str) -> str:
    return "/".join(url.split("/")[3:5])


def normalize_symptom(value: Any) -> str:
    symptom = str(value or "")
    if symptom == "Security vulnerability":
        return "Security Vulnerability"
    if symptom.startswith("other:") or symptom not in SYMPTOM_ORDER:
        return "Other"
    return symptom


def canonical_layers(record: dict[str, Any]) -> list[str]:
    layers: list[str] = []
    valid = set(LAYER_ORDER) - {"Other"}
    raw_layers = [
        item.get("layer")
        for item in record.get("root_causes", [])
        if isinstance(item, dict) and item.get("layer")
    ]
    if not raw_layers:
        raw_layers = record.get("root_cause_layers") or []
    for raw_layer in raw_layers:
        layer = raw_layer if raw_layer in valid else "Other"
        if layer not in layers:
            layers.append(layer)
    return layers


def concentration(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    all_values: list[float] = []
    projects: dict[str, Any] = {}
    for repo, project in payload["projects"].items():
        values = sorted(
            (
                float(item.get("weighted_bug_sum", 0))
                for item in project.get("files", [])
                if float(item.get("weighted_bug_sum", 0)) > 0
            ),
            reverse=True,
        )
        all_values.extend(values)
        top_count = math.ceil(0.2 * len(values))
        projects[PROJECT_LABELS.get(repo, repo)] = {
            "entity_count": len(values),
            "weighted_bug_total": sum(values),
            "top_20_percent_cover": sum(values[:top_count]) / sum(values),
        }
    all_values.sort(reverse=True)
    top_count = math.ceil(0.2 * len(all_values))
    return {
        "entity_count": len(all_values),
        "weighted_bug_total": sum(all_values),
        "top_20_percent_cover": sum(all_values[:top_count]) / sum(all_values),
        "projects": projects,
    }


def build_rq1() -> dict[str, Any]:
    bugs = load_json(BUGS_PATH)
    symptoms: Counter[str] = Counter()
    project_symptoms: dict[str, Counter[str]] = defaultdict(Counter)
    layer_weights: Counter[str] = Counter()
    layer_symptoms: dict[str, Counter[str]] = defaultdict(Counter)

    for url, record in bugs.items():
        symptom = normalize_symptom(record.get("symptom"))
        symptoms[symptom] += 1
        project = PROJECT_LABELS.get(project_from_url(url), project_from_url(url))
        project_symptoms[project][symptom] += 1
        layers = canonical_layers(record)
        if not layers:
            raise ValueError(f"Canonical record has no architectural layer: {url}")
        weight = 1.0 / len(layers)
        for layer in layers:
            layer_weights[layer] += weight
            layer_symptoms[layer][symptom] += weight

    total = len(bugs)
    if total != 12_707 or not math.isclose(sum(layer_weights.values()), total, abs_tol=1e-8):
        raise ValueError("RQ1 corpus or layer weights do not match canonical anchors")

    project_rows: list[dict[str, Any]] = []
    for project in PROJECT_ORDER:
        counts = project_symptoms[project]
        project_total = sum(counts.values())
        leading, leading_count = counts.most_common(1)[0]
        project_rows.append(
            {
                "project": project,
                "fixes": project_total,
                "leading_symptom": leading,
                "leading_symptom_count": leading_count,
                "leading_symptom_share": leading_count / project_total,
                "top_three_share": sum(value for _, value in counts.most_common(3)) / project_total,
            }
        )

    association_specs = (
        ("Build/Release", "Build/Compilation Error"),
        ("Config/Entrypoint", "API/argument parsing Error"),
        ("Hardware Adaptation", "Hardware/Backend Compatibility Issue"),
    )
    associations: list[dict[str, Any]] = []
    for layer, symptom in association_specs:
        cell = layer_symptoms[layer][symptom]
        layer_total = layer_weights[layer]
        lift = (cell / symptoms[symptom]) / (layer_total / total)
        associations.append(
            {
                "architectural_layer": layer,
                "symptom": symptom,
                "weighted_association": cell,
                "weighted_layer_total": layer_total,
                "within_layer_share": cell / layer_total,
                "lift": lift,
            }
        )

    critical = sum(
        symptoms[name]
        for name in ("Incorrect/Inaccuracy Output", "Runtime Crash", "Model Loading Error")
    )
    return {
        "schema_version": 1,
        "inputs": {str(BUGS_PATH.relative_to(ROOT)): sha256(BUGS_PATH)},
        "counting_rule": "one normalized symptom per fix; distinct architectural layers receive 1/k weight",
        "canonical_fixes": total,
        "symptom_counts": {name: symptoms[name] for name in SYMPTOM_ORDER},
        "correctness_or_availability_fixes": critical,
        "correctness_or_availability_share": critical / total,
        "project_symptom_summary": project_rows,
        "weighted_layer_totals": {name: layer_weights[name] for name in LAYER_ORDER},
        "selected_symptom_layer_associations": associations,
    }


def build_rq2() -> dict[str, Any]:
    operations = load_json(OPERATIONS_PATH)
    instance_counts: Counter[tuple[str, str]] = Counter()
    operation_counts: Counter[str] = Counter()
    for record in operations.values():
        operation = (record.get("fix_pattern_analysis") or {}).get("repair_pattern")
        if operation not in MAJOR_OPERATIONS:
            continue
        for root_cause in record.get("root_causes") or []:
            layer = root_cause.get("layer") if isinstance(root_cause, dict) else None
            if layer and layer != "Other":
                instance_counts[(layer, operation)] += 1
                operation_counts[operation] += 1

    instances = sum(operation_counts.values())
    dominant = operation_counts["Correction"] + operation_counts["Adaptation"]
    if instances != 19_965 or dominant != 14_702:
        raise ValueError("RQ2 repair-operation counts do not match canonical anchors")

    layer_summary: list[dict[str, Any]] = []
    principal_layers = [name for name in LAYER_ORDER if name != "Other"]
    for layer in principal_layers:
        total = sum(instance_counts[layer, operation] for operation in MAJOR_OPERATIONS)
        logic_adaptation = instance_counts[layer, "Correction"] + instance_counts[layer, "Adaptation"]
        layer_summary.append(
            {
                "architectural_layer": layer,
                "instances": total,
                "logic_correction_and_adaptation_share": logic_adaptation / total,
                "configuration_share": instance_counts[layer, "Configuration"] / total,
            }
        )

    fix_size = load_json(FIX_SIZE_PATH)
    return {
        "schema_version": 1,
        "inputs": {
            str(OPERATIONS_PATH.relative_to(ROOT)): sha256(OPERATIONS_PATH),
            str(FILE_DISTRIBUTION_PATH.relative_to(ROOT)): sha256(FILE_DISTRIBUTION_PATH),
            str(FUNCTION_DISTRIBUTION_PATH.relative_to(ROOT)): sha256(FUNCTION_DISTRIBUTION_PATH),
            str(FIX_SIZE_PATH.relative_to(ROOT)): sha256(FIX_SIZE_PATH),
        },
        "repair_operation_counting_rule": "one operation instance per recorded root-cause entry in the eight principal layers; residual operations excluded",
        "repair_operation_instances": instances,
        "logic_correction_and_adaptation_instances": dominant,
        "logic_correction_and_adaptation_share": dominant / instances,
        "operation_instances": {
            DISPLAY_OPERATION.get(name, name): operation_counts[name] for name in MAJOR_OPERATIONS
        },
        "repair_operation_counts": [
            {
                "architectural_layer": layer,
                "repair_operation": DISPLAY_OPERATION.get(operation, operation),
                "count": count,
            }
            for (layer, operation), count in sorted(instance_counts.items())
        ],
        "architectural_layer_summary": layer_summary,
        "file_concentration": concentration(FILE_DISTRIBUTION_PATH),
        "function_concentration": concentration(FUNCTION_DISTRIBUTION_PATH),
        "fix_size_overall": fix_size["overall"],
        "fix_size_by_file_bucket": fix_size["by_file_bucket"],
        "patch_derivation_note": "complete diffs are not redistributed; fix_size_stats.json contains the published per-PR derived measures",
    }


def build_rq3() -> dict[str, Any]:
    breadth = load_json(FILE_BREADTH_PATH)
    layer_payload = load_json(RQ3_LAYER_PATH)
    first = breadth["table"]["2023-01"]
    last = breadth["table"]["2026-03"]
    return {
        "schema_version": 1,
        "inputs": {
            str(FILE_BREADTH_PATH.relative_to(ROOT)): sha256(FILE_BREADTH_PATH),
            str(RQ3_LAYER_PATH.relative_to(ROOT)): sha256(RQ3_LAYER_PATH),
        },
        "analysis_window": {
            "start_month": "2023-01",
            "end_month": "2026-03",
            "fixes": layer_payload["analysis"]["window_fixes"],
            "months": layer_payload["analysis"]["month_count"],
        },
        "file_breadth_first_month": first,
        "file_breadth_last_month": last,
        "architectural_layer_trends": layer_payload["layer_results"],
        "interpretation_boundary": "monthly layer shares are compositional and describe observed fixing activity, not causal changes in reliability",
    }


def pct(value: float, digits: int = 1) -> str:
    return f"{fixed(100 * value, digits)}%"


def fixed(value: float, digits: int = 1) -> str:
    quantum = Decimal("1").scaleb(-digits)
    return format(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP), f".{digits}f")


def rq1_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# RQ1: Failure localization",
        "",
        "This report is generated from the public 12,707-fix corpus by `scripts/generate_reports.py`.",
        "Each fix has one normalized symptom. Distinct architectural layers receive `1/k` weight, so every fix contributes total weight one.",
        "",
        "## Corpus anchors",
        "",
        f"- Canonical fixes: **{payload['canonical_fixes']:,}**",
        f"- Incorrect output, runtime crash, and model-loading fixes: **{payload['correctness_or_availability_fixes']:,} ({pct(payload['correctness_or_availability_share'])})**",
        "",
        "## Symptom distribution",
        "",
        "| Symptom | Fixes | Share |",
        "|---|---:|---:|",
    ]
    for symptom, count in payload["symptom_counts"].items():
        lines.append(f"| {symptom} | {count:,} | {100 * count / payload['canonical_fixes']:.1f}% |")
    lines += [
        "",
        "## Project profiles",
        "",
        "| Project | Fixes | Leading symptom | Leading share | Top-three share |",
        "|---|---:|---|---:|---:|",
    ]
    for row in payload["project_symptom_summary"]:
        lines.append(
            f"| {row['project']} | {row['fixes']:,} | {row['leading_symptom']} | "
            f"{pct(row['leading_symptom_share'])} | {pct(row['top_three_share'])} |"
        )
    lines += [
        "",
        "## Weighted architectural-layer totals",
        "",
        "| Architectural layer | Weighted fixes | Share |",
        "|---|---:|---:|",
    ]
    for layer, value in payload["weighted_layer_totals"].items():
        lines.append(f"| {layer} | {value:,.1f} | {100 * value / payload['canonical_fixes']:.1f}% |")
    lines += [
        "",
        "## Selected symptom-layer associations reported in the paper",
        "",
        "| Architectural layer | Symptom | Weighted association | Layer total | Within-layer share | Lift |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in payload["selected_symptom_layer_associations"]:
        lines.append(
            f"| {row['architectural_layer']} | {row['symptom']} | {row['weighted_association']:.1f} | "
            f"{row['weighted_layer_total']:.1f} | {pct(row['within_layer_share'])} | {row['lift']:.2f} |"
        )
    lines += [
        "",
        "Figures are available under `figures/generated/` and the exact manuscript figures under `paper/fig/`.",
        "Lift is descriptive association, not causal evidence or a measured localization success rate.",
    ]
    return "\n".join(lines) + "\n"


def rq2_markdown(payload: dict[str, Any]) -> str:
    files = payload["file_concentration"]
    functions = payload["function_concentration"]
    lines = [
        "# RQ2: Repair structure",
        "",
        "This report is generated from the public repair-operation annotations and published derived file/function and patch measures.",
        "",
        "## Repair operations",
        "",
        f"- Layer-specific repair-operation instances: **{payload['repair_operation_instances']:,}**",
        f"- Logic Correction + Adaptation: **{payload['logic_correction_and_adaptation_instances']:,} ({pct(payload['logic_correction_and_adaptation_share'])})**",
        "",
        "| Repair operation | Instances | Share |",
        "|---|---:|---:|",
    ]
    for operation, count in payload["operation_instances"].items():
        lines.append(f"| {operation} | {count:,} | {100 * count / payload['repair_operation_instances']:.1f}% |")
    lines += [
        "",
        "The full architectural-layer × repair-operation table is `results/repair_operation_counts.csv`.",
        "",
        "## File and function concentration",
        "",
        "| Scope | Entities | Weighted bug total | Top 20% coverage |",
        "|---|---:|---:|---:|",
        f"| Files | {files['entity_count']:,} | {files['weighted_bug_total']:,.1f} | {pct(files['top_20_percent_cover'])} |",
        f"| Functions | {functions['entity_count']:,} | {functions['weighted_bug_total']:,.1f} | {pct(functions['top_20_percent_cover'])} |",
        "",
        "| Project | File top-20% coverage | Function top-20% coverage |",
        "|---|---:|---:|",
    ]
    for project in PROJECT_ORDER:
        lines.append(
            f"| {project} | {pct(files['projects'][project]['top_20_percent_cover'])} | "
            f"{pct(functions['projects'][project]['top_20_percent_cover'])} |"
        )
    overall = payload["fix_size_overall"]
    lines += [
        "",
        "## Fix size",
        "",
        "| Fixes | Median lines | P75 | P90 | P95 |",
        "|---:|---:|---:|---:|---:|",
        f"| {overall['count']:,} | {overall['median']:g} | {overall['p75']:g} | {overall['p90']:g} | {overall['p95']:g} |",
        "",
        "| Modified-file bucket | Fixes | Median changed lines | P90 changed lines |",
        "|---|---:|---:|---:|",
    ]
    for row in payload["fix_size_by_file_bucket"]:
        lines.append(f"| {row['group']} | {row['count']:,} | {row['median']:g} | {row['p90']:g} |")
    lines += [
        "",
        "Complete upstream patches are not redistributed. The per-PR derived measures in `data/fix_size_stats.json` preserve the published quantities.",
    ]
    return "\n".join(lines) + "\n"


def rq3_markdown(payload: dict[str, Any]) -> str:
    window = payload["analysis_window"]
    first = payload["file_breadth_first_month"]
    last = payload["file_breadth_last_month"]
    lines = [
        "# RQ3: Repair evolution",
        "",
        f"The formal window contains **{window['fixes']:,} fixes across {window['months']} months** ({window['start_month']} to {window['end_month']}).",
        "",
        "## File-breadth endpoints",
        "",
        "| Bucket | January 2023 | March 2026 |",
        "|---|---:|---:|",
    ]
    for bucket in ("1 file", "2-5 files", "6+ files"):
        lines.append(
            f"| {bucket} | {first[bucket]['count']:,} ({fixed(first[bucket]['percentage'])}%) | "
            f"{last[bucket]['count']:,} ({fixed(last[bucket]['percentage'])}%) |"
        )
    lines += [
        "",
        "## Architectural-composition trends",
        "",
        "| Architectural layer | First 12m | Last 12m | Delta pp | Pooled rho | Adjusted rho | Pooled pp/year | Adjusted pp/year |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["architectural_layer_trends"]:
        lines.append(
            f"| {row['layer']} | {row['first_window_mean_monthly_share_pct']:.1f}% | "
            f"{row['last_window_mean_monthly_share_pct']:.1f}% | {row['change_percentage_points']:+.1f} | "
            f"{row['pooled_spearman_rho']:.3f} | {row['adjusted_spearman_rho']:.3f} | "
            f"{row['pooled_slope_pp_per_year']:+.1f} | {row['adjusted_slope_pp_per_year']:+.1f} |"
        )
    lines += [
        "",
        "Full-precision p-values, BH-adjusted q-values, monthly series, fixed project weights, and per-project trends are under `results/rq3_layer_trends/`.",
        "Monthly layer shares are compositional and describe observed fixing activity; they do not establish causal changes in a layer's reliability.",
    ]
    return "\n".join(lines) + "\n"


def reports_readme() -> str:
    return """# Reproduced analysis reports

This directory contains one current, human-readable report for each research
question in the manuscript. Regenerate them with:

```bash
python scripts/generate_reports.py
```

Verify that the checked-in reports and machine-readable summaries are current
without rewriting files:

```bash
python scripts/generate_reports.py --check
```

- `rq1_failure_localization.md`: symptom distributions, weighted architectural
  layers, and selected lift associations.
- `rq2_repair_structure.md`: repair-operation counts, file/function
  concentration, and fix-size summaries.
- `rq3_repair_evolution.md`: file-breadth endpoints and architectural-layer
  trends.

Historical exploratory reports, reports based on the superseded 12,961/12,963
record corpora, refetch logs, and manuscript previews are intentionally not
part of the public artifact.
"""


def repair_operation_csv(payload: dict[str, Any]) -> str:
    lines = ["architectural_layer,repair_operation,count"]
    for row in payload["repair_operation_counts"]:
        lines.append(
            f"{row['architectural_layer']},{row['repair_operation']},{row['count']}"
        )
    return "\n".join(lines) + "\n"


def render_outputs() -> dict[Path, str]:
    rq1 = build_rq1()
    rq2 = build_rq2()
    rq3 = build_rq3()
    json_options = {"ensure_ascii": False, "indent": 2}
    return {
        RESULTS / "rq1_failure_localization.json": json.dumps(rq1, **json_options) + "\n",
        RESULTS / "rq2_repair_structure.json": json.dumps(rq2, **json_options) + "\n",
        RESULTS / "rq3_repair_evolution.json": json.dumps(rq3, **json_options) + "\n",
        RESULTS / "repair_operation_counts.csv": repair_operation_csv(rq2),
        REPORTS / "README.md": reports_readme(),
        REPORTS / "rq1_failure_localization.md": rq1_markdown(rq1),
        REPORTS / "rq2_repair_structure.md": rq2_markdown(rq2),
        REPORTS / "rq3_repair_evolution.md": rq3_markdown(rq3),
    }


def main() -> None:
    args = parse_args()
    outputs = render_outputs()
    stale: list[str] = []
    for path, content in outputs.items():
        relative = path.relative_to(ROOT).as_posix()
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
            print(f"Wrote {relative}")
    if stale:
        raise SystemExit("Stale or missing generated files: " + ", ".join(stale))
    if args.check:
        print(f"Report check passed for {len(outputs)} files")


if __name__ == "__main__":
    main()
