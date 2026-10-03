#!/usr/bin/env python3
"""Reproduce the canonical RQ3 architectural-composition trend analysis.

The analysis starts from the manually validated bug records and PR creation
timestamps.  It does not read values back from the manuscript.  By default it
reproduces the January 2023--March 2026 analysis window used in the paper and
writes deterministic JSON/CSV/Markdown artifacts.

Counting rules
--------------
* Keep manually verified, fixed, merged bug-fixing PRs.
* Deduplicate a bug's architectural layers.
* A bug assigned to k layers contributes 1/k to each layer.
* Monthly pooled shares therefore sum to 100 percent.
* Project-standardized shares use fixed project weights from the full analysis
  window.  In months where a project has no fixes, weights are renormalized
  over the active projects.
* First/last-window shares are equal-weight means of monthly shares, not shares
  pooled over all fixes in each window.
* Two-sided permutation p-values use a fixed seed and the add-one correction.
  Benjamini--Hochberg correction is applied across the nine layer tests.

Example
-------
    python scripts/analyze_rq3_layer_trends.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BUGS = ROOT / "data" / "final_bug_results_with_root_cause_completed_symptom.json"
DEFAULT_TIMESTAMPS = ROOT / "data" / "bug_timestamps.json"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "rq3_layer_trends"
DEFAULT_REPORT = ROOT / "reports" / "rq3_layer_trends.md"

START_MONTH = "2023-01"
END_MONTH = "2026-03"
WINDOW_MONTHS = 12
PERMUTATIONS = 20_000
RANDOM_SEED = 2_026

EXPECTED_CANONICAL_FIXES = 12_707
EXPECTED_WINDOW_FIXES = 12_299
EXPECTED_MONTHS = 39
EXPECTED_PROJECTS = 6
EXPECTED_LAYERS = 9

PROJECT_DISPLAY_NAMES = {
    "DeepSpeed": "DeepSpeed",
    "TensorRT-LLM": "TensorRT-LLM",
    "llama.cpp": "llama.cpp",
    "mlc-llm": "MLC-LLM",
    "text-generation-inference": "TGI",
    "vllm": "vLLM",
}

# Display order used by the manuscript table.
LAYER_ORDER = (
    "Hardware Adaptation",
    "Tests/Bench",
    "Config/Entrypoint",
    "Compiler/Optimization",
    "Scheduler/Runtime",
    "Docs",
    "Operators/Backend",
    "Other",
    "Build/Release",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bugs", type=Path, default=DEFAULT_BUGS)
    parser.add_argument("--timestamps", type=Path, default=DEFAULT_TIMESTAMPS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--start-month", default=START_MONTH, help="Inclusive YYYY-MM")
    parser.add_argument("--end-month", default=END_MONTH, help="Inclusive YYYY-MM")
    parser.add_argument("--window-months", type=int, default=WINDOW_MONTHS)
    parser.add_argument("--permutations", type=int, default=PERMUTATIONS)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument(
        "--no-canonical-checks",
        action="store_true",
        help="Allow alternative inputs/windows without canonical corpus assertions.",
    )
    return parser.parse_args()


def month_range(start: str, end: str) -> list[str]:
    try:
        start_year, start_month = map(int, start.split("-"))
        end_year, end_month = map(int, end.split("-"))
    except ValueError as exc:
        raise ValueError("Months must use YYYY-MM format") from exc
    if not (1 <= start_month <= 12 and 1 <= end_month <= 12):
        raise ValueError("Month numbers must be between 01 and 12")
    start_index = start_year * 12 + start_month - 1
    end_index = end_year * 12 + end_month - 1
    if start_index > end_index:
        raise ValueError("start-month must not be after end-month")
    return [f"{index // 12:04d}-{index % 12 + 1:02d}" for index in range(start_index, end_index + 1)]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def portable_path(path: Path) -> str:
    """Return a repository-relative path when the input is inside the artifact."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return str(resolved)


def project_from_url(url: str) -> str:
    parts = url.split("/")
    if len(parts) < 7 or parts[2] != "github.com" or parts[5] != "pull":
        raise ValueError(f"Unexpected GitHub pull-request URL: {url}")
    return parts[4]


def assigned_layers(bug: dict[str, Any]) -> tuple[str, ...]:
    # root_causes[].layer contains the manually saved canonical assignments.
    # root_cause_layers is retained only as a fallback for legacy records; it is
    # a derived convenience field and can lag a manual correction.
    raw_layers = [item.get("layer") for item in bug.get("root_causes", [])]
    if not any(raw_layers):
        raw_layers = bug.get("root_cause_layers")
    layers = tuple(sorted({str(layer).strip() for layer in raw_layers or [] if layer}))
    return layers or ("Other",)


def is_canonical_fix(bug: dict[str, Any]) -> bool:
    return (
        bug.get("is_bug_related") is True
        and str(bug.get("status", "")).lower() == "fixed"
        and str(bug.get("pr_status", "")).lower() == "merged"
    )


def load_records(
    bugs_path: Path,
    timestamps_path: Path,
    start_month: str,
    end_month: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    bugs = json.loads(bugs_path.read_text(encoding="utf-8"))
    timestamps = json.loads(timestamps_path.read_text(encoding="utf-8"))
    if not isinstance(bugs, dict) or not isinstance(timestamps, dict):
        raise TypeError("Both input files must contain JSON objects keyed by PR URL")

    canonical_urls = [url for url, bug in bugs.items() if is_canonical_fix(bug)]
    layer_field_disagreements = 0
    for url in canonical_urls:
        bug = bugs[url]
        manual = {item.get("layer") for item in bug.get("root_causes", []) if item.get("layer")}
        derived = {layer for layer in bug.get("root_cause_layers", []) if layer}
        if manual and derived and manual != derived:
            layer_field_disagreements += 1
    missing_timestamps = sorted(url for url in canonical_urls if url not in timestamps)
    if missing_timestamps:
        preview = ", ".join(missing_timestamps[:3])
        raise ValueError(f"{len(missing_timestamps)} canonical fixes lack timestamps: {preview}")

    records: list[dict[str, Any]] = []
    for url in canonical_urls:
        month = str(timestamps[url])[:7]
        if start_month <= month <= end_month:
            records.append(
                {
                    "url": url,
                    "project": project_from_url(url),
                    "month": month,
                    "layers": assigned_layers(bugs[url]),
                }
            )
    records.sort(key=lambda row: (row["month"], row["project"], row["url"]))
    diagnostics = {
        "input_bug_records": len(bugs),
        "input_timestamp_records": len(timestamps),
        "canonical_fixes": len(canonical_urls),
        "canonical_fixes_with_timestamps": len(canonical_urls) - len(missing_timestamps),
        "canonical_layer_field_disagreements": layer_field_disagreements,
        "window_fixes": len(records),
    }
    return records, diagnostics


def average_ranks(values: Iterable[float]) -> np.ndarray:
    array = np.asarray(list(values), dtype=float)
    order = np.argsort(array, kind="mergesort")
    ranks = np.empty(len(array), dtype=float)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and array[order[end]] == array[order[start]]:
            end += 1
        ranks[order[start:end]] = (start + 1 + end) / 2
        start = end
    return ranks


def spearman(values_x: Sequence[float], values_y: Sequence[float]) -> float:
    ranks_x = average_ranks(values_x)
    ranks_y = average_ranks(values_y)
    if np.all(ranks_x == ranks_x[0]) or np.all(ranks_y == ranks_y[0]):
        return float("nan")
    return float(np.corrcoef(ranks_x, ranks_y)[0, 1])


def permutation_p_values(
    series_by_name: dict[str, Sequence[float]],
    permutations: int,
    seed: int,
) -> dict[str, float]:
    """Return deterministic two-sided Spearman permutation p-values."""
    if permutations < 1:
        raise ValueError("permutations must be positive")
    names = list(series_by_name)
    sample_size = len(next(iter(series_by_name.values())))
    if any(len(values) != sample_size for values in series_by_name.values()):
        raise ValueError("All permutation-test series must have equal length")

    time_ranks = average_ranks(range(sample_size))
    time_centered = time_ranks - time_ranks.mean()
    time_norm = np.sqrt(np.sum(time_centered**2))
    centered = np.column_stack(
        [average_ranks(series_by_name[name]) - average_ranks(series_by_name[name]).mean() for name in names]
    )
    norms = time_norm * np.sqrt(np.sum(centered**2, axis=0))
    observed = (time_centered @ centered) / norms
    exceedances = np.zeros(len(names), dtype=np.int64)
    rng = np.random.default_rng(seed)
    for _ in range(permutations):
        permuted_time = time_centered[rng.permutation(sample_size)]
        permuted = (permuted_time @ centered) / norms
        exceedances += np.abs(permuted) >= np.abs(observed) - 1e-15
    return {
        name: float((exceedances[index] + 1) / (permutations + 1))
        for index, name in enumerate(names)
    }


def benjamini_hochberg(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values, key=p_values.get)
    count = len(ordered)
    adjusted: dict[str, float] = {}
    running_minimum = 1.0
    for rank in range(count, 0, -1):
        name = ordered[rank - 1]
        running_minimum = min(running_minimum, p_values[name] * count / rank)
        adjusted[name] = float(min(1.0, running_minimum))
    return adjusted


def annual_slope(shares: Sequence[float], month_indices: Sequence[float] | None = None) -> float:
    time = (
        np.arange(len(shares), dtype=float)
        if month_indices is None
        else np.asarray(month_indices, dtype=float)
    )
    return float(np.polyfit(time, shares, 1)[0] * 12)


def compute_analysis(
    records: list[dict[str, Any]],
    months: list[str],
    window_months: int,
    permutations: int,
    seed: int,
) -> dict[str, Any]:
    if window_months < 1 or 2 * window_months > len(months):
        raise ValueError("window-months must be positive and fit twice in the analysis period")

    projects = sorted({row["project"] for row in records})
    observed_layers = {layer for row in records for layer in row["layers"]}
    unknown_layers = observed_layers - set(LAYER_ORDER)
    missing_layers = set(LAYER_ORDER) - observed_layers
    if unknown_layers or missing_layers:
        raise ValueError(
            f"Layer taxonomy mismatch; unknown={sorted(unknown_layers)}, missing={sorted(missing_layers)}"
        )

    monthly_counts: Counter[str] = Counter()
    project_counts: Counter[str] = Counter()
    project_month_counts: Counter[tuple[str, str]] = Counter()
    pooled_weights: dict[str, Counter[str]] = defaultdict(Counter)
    project_month_weights: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for row in records:
        month = row["month"]
        project = row["project"]
        monthly_counts[month] += 1
        project_counts[project] += 1
        project_month_counts[project, month] += 1
        contribution = 1.0 / len(row["layers"])
        for layer in row["layers"]:
            pooled_weights[month][layer] += contribution
            project_month_weights[project, month][layer] += contribution

    empty_months = [month for month in months if monthly_counts[month] == 0]
    if empty_months:
        raise ValueError(f"Analysis window contains months without fixes: {empty_months}")

    fixed_project_weights = {
        project: project_counts[project] / len(records) for project in projects
    }
    pooled_series: dict[str, list[float]] = {layer: [] for layer in LAYER_ORDER}
    adjusted_series: dict[str, list[float]] = {layer: [] for layer in LAYER_ORDER}
    monthly_rows: list[dict[str, Any]] = []
    project_month_rows: list[dict[str, Any]] = []

    for month in months:
        active_projects = [project for project in projects if project_month_counts[project, month]]
        active_weight = sum(fixed_project_weights[project] for project in active_projects)
        row: dict[str, Any] = {
            "month": month,
            "fix_count": monthly_counts[month],
            "active_projects": len(active_projects),
        }
        for layer in LAYER_ORDER:
            pooled_share = 100 * pooled_weights[month][layer] / monthly_counts[month]
            adjusted_share = sum(
                fixed_project_weights[project]
                / active_weight
                * 100
                * project_month_weights[project, month][layer]
                / project_month_counts[project, month]
                for project in active_projects
            )
            pooled_series[layer].append(float(pooled_share))
            adjusted_series[layer].append(float(adjusted_share))
            row[f"pooled_{layer}"] = float(pooled_share)
            row[f"adjusted_{layer}"] = float(adjusted_share)
        monthly_rows.append(row)

        for project in active_projects:
            project_row: dict[str, Any] = {
                "month": month,
                "project": PROJECT_DISPLAY_NAMES.get(project, project),
                "fix_count": project_month_counts[project, month],
                "renormalized_project_weight": fixed_project_weights[project] / active_weight,
            }
            for layer in LAYER_ORDER:
                project_row[layer] = float(
                    100
                    * project_month_weights[project, month][layer]
                    / project_month_counts[project, month]
                )
            project_month_rows.append(project_row)

    pooled_p = permutation_p_values(pooled_series, permutations, seed)
    adjusted_p = permutation_p_values(adjusted_series, permutations, seed + 1)
    pooled_q = benjamini_hochberg(pooled_p)
    adjusted_q = benjamini_hochberg(adjusted_p)
    time = list(range(len(months)))
    layer_results: list[dict[str, Any]] = []
    for layer in LAYER_ORDER:
        pooled = pooled_series[layer]
        adjusted = adjusted_series[layer]
        first_mean = float(np.mean(pooled[:window_months]))
        last_mean = float(np.mean(pooled[-window_months:]))
        layer_results.append(
            {
                "layer": layer,
                "first_window_mean_monthly_share_pct": first_mean,
                "last_window_mean_monthly_share_pct": last_mean,
                "change_percentage_points": last_mean - first_mean,
                "pooled_spearman_rho": spearman(time, pooled),
                "pooled_permutation_p": pooled_p[layer],
                "pooled_bh_q": pooled_q[layer],
                "pooled_slope_pp_per_year": annual_slope(pooled),
                "adjusted_spearman_rho": spearman(time, adjusted),
                "adjusted_permutation_p": adjusted_p[layer],
                "adjusted_bh_q": adjusted_q[layer],
                "adjusted_slope_pp_per_year": annual_slope(adjusted),
            }
        )

    per_project_results: list[dict[str, Any]] = []
    for project in projects:
        project_months = [month for month in months if project_month_counts[project, month]]
        project_time = [months.index(month) for month in project_months]
        for layer in LAYER_ORDER:
            shares = [
                100
                * project_month_weights[project, month][layer]
                / project_month_counts[project, month]
                for month in project_months
            ]
            per_project_results.append(
                {
                    "project": PROJECT_DISPLAY_NAMES.get(project, project),
                    "layer": layer,
                    "fix_count": project_counts[project],
                    "active_months": len(project_months),
                    "first_active_month": project_months[0],
                    "last_active_month": project_months[-1],
                    "spearman_rho": spearman(project_time, shares),
                    "slope_pp_per_year": annual_slope(shares, project_time),
                }
            )

    return {
        "projects": projects,
        "project_counts": dict(project_counts),
        "fixed_project_weights": fixed_project_weights,
        "monthly_rows": monthly_rows,
        "project_month_rows": project_month_rows,
        "layer_results": layer_results,
        "per_project_results": per_project_results,
    }


def canonical_checks(
    diagnostics: dict[str, int], months: list[str], analysis: dict[str, Any]
) -> None:
    expected = {
        "canonical_fixes": EXPECTED_CANONICAL_FIXES,
        "window_fixes": EXPECTED_WINDOW_FIXES,
    }
    for key, value in expected.items():
        if diagnostics[key] != value:
            raise AssertionError(f"Expected {key}={value:,}, observed {diagnostics[key]:,}")
    if len(months) != EXPECTED_MONTHS:
        raise AssertionError(f"Expected {EXPECTED_MONTHS} months, observed {len(months)}")
    if len(analysis["projects"]) != EXPECTED_PROJECTS:
        raise AssertionError(
            f"Expected {EXPECTED_PROJECTS} projects, observed {len(analysis['projects'])}"
        )
    if len(analysis["layer_results"]) != EXPECTED_LAYERS:
        raise AssertionError(
            f"Expected {EXPECTED_LAYERS} layers, observed {len(analysis['layer_results'])}"
        )
    for row in analysis["monthly_rows"]:
        pooled_total = sum(row[f"pooled_{layer}"] for layer in LAYER_ORDER)
        adjusted_total = sum(row[f"adjusted_{layer}"] for layer in LAYER_ORDER)
        if not np.isclose(pooled_total, 100.0, atol=1e-9):
            raise AssertionError(f"Pooled shares for {row['month']} sum to {pooled_total}")
        if not np.isclose(adjusted_total, 100.0, atol=1e-9):
            raise AssertionError(f"Adjusted shares for {row['month']} sum to {adjusted_total}")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, payload: dict[str, Any]) -> None:
    metadata = payload["analysis"]
    lines = [
        "# Canonical RQ3 architectural-composition trends",
        "",
        f"- Period: **{metadata['start_month']} to {metadata['end_month']}** ({metadata['month_count']} months)",
        f"- Included fixes: **{metadata['window_fixes']:,}**",
        f"- Weighting: distinct layers, **1/k per layer and bug**",
        f"- Permutation test: **{metadata['permutations']:,}** two-sided permutations, seed **{metadata['seed']}**",
        f"- Window summaries: equal-weight means of the first and last **{metadata['window_months']} monthly shares**",
        "",
        "## Layer trends",
        "",
        f"| Layer | First {metadata['window_months']}m | Last {metadata['window_months']}m | Delta pp | rho | p | q | rho adjusted | Pooled pp/year | Adjusted pp/year |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["layer_results"]:
        lines.append(
            "| {layer} | {first:.3f}% | {last:.3f}% | {delta:+.3f} | {rho:.6f} | {p:.6g} | {q:.6g} | {rho_adj:.6f} | {slope:+.4f} | {slope_adj:+.4f} |".format(
                layer=row["layer"],
                first=row["first_window_mean_monthly_share_pct"],
                last=row["last_window_mean_monthly_share_pct"],
                delta=row["change_percentage_points"],
                rho=row["pooled_spearman_rho"],
                p=row["pooled_permutation_p"],
                q=row["pooled_bh_q"],
                rho_adj=row["adjusted_spearman_rho"],
                slope=row["pooled_slope_pp_per_year"],
                slope_adj=row["adjusted_slope_pp_per_year"],
            )
        )
    lines.extend(
        [
            "",
            "`First 12m` and `Last 12m` are means of monthly shares. Delta is computed from unrounded values. Pooled and adjusted slopes are least-squares percentage-point changes per year.",
            "",
            "## Fixed project weights",
            "",
            "| Project | Fixes | Weight |",
            "|---|---:|---:|",
        ]
    )
    for project in sorted(payload["project_counts"]):
        lines.append(
            f"| {PROJECT_DISPLAY_NAMES.get(project, project)} | {payload['project_counts'][project]:,} | {payload['fixed_project_weights'][project]:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Reproduction",
            "",
            "```bash",
            "python scripts/analyze_rq3_layer_trends.py",
            "```",
            "",
            "The JSON output records the input SHA-256 hashes, filtering rules, parameters, full-precision statistics, and per-project trends. CSV files contain the pooled/standardized monthly series and active project-month series.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    months = month_range(args.start_month, args.end_month)
    records, diagnostics = load_records(
        args.bugs.resolve(), args.timestamps.resolve(), args.start_month, args.end_month
    )
    analysis = compute_analysis(records, months, args.window_months, args.permutations, args.seed)
    if not args.no_canonical_checks:
        if args.start_month != START_MONTH or args.end_month != END_MONTH:
            raise ValueError("Use --no-canonical-checks when changing the formal analysis window")
        canonical_checks(diagnostics, months, analysis)

    payload = {
        "schema_version": 1,
        "analysis": {
            **diagnostics,
            "start_month": args.start_month,
            "end_month": args.end_month,
            "month_count": len(months),
            "window_months": args.window_months,
            "permutations": args.permutations,
            "seed": args.seed,
            "permutation_test": "two-sided Spearman; (exceedances + 1) / (permutations + 1)",
            "multiple_testing": "Benjamini-Hochberg across nine architectural layers",
            "first_last_summary": "equal-weight arithmetic mean of monthly shares",
            "slope_unit": "percentage points per year",
            "canonical_checks_enabled": not args.no_canonical_checks,
        },
        "inputs": {
            "bugs": {"path": portable_path(args.bugs), "sha256": sha256(args.bugs.resolve())},
            "timestamps": {
                "path": portable_path(args.timestamps),
                "sha256": sha256(args.timestamps.resolve()),
            },
        },
        "filters": {
            "is_bug_related": True,
            "status_case_insensitive": "fixed",
            "pr_status_case_insensitive": "merged",
            "timestamp": "PR creation month",
        },
        "layer_weighting": "deduplicate assigned layers; contribute 1/k to each of k layers",
        "project_standardization": "fixed full-window project weights, renormalized over active projects each month",
        "project_counts": analysis["project_counts"],
        "fixed_project_weights": analysis["fixed_project_weights"],
        "layer_results": analysis["layer_results"],
        "per_project_results": analysis["per_project_results"],
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    results_path = args.output_dir / "rq3_layer_trend_results.json"
    monthly_path = args.output_dir / "rq3_monthly_layer_shares.csv"
    project_monthly_path = args.output_dir / "rq3_project_monthly_layer_shares.csv"
    results_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(monthly_path, analysis["monthly_rows"])
    write_csv(project_monthly_path, analysis["project_month_rows"])
    write_report(args.report, payload)

    hardware = next(row for row in analysis["layer_results"] if row["layer"] == "Hardware Adaptation")
    print(f"Canonical fixes: {diagnostics['canonical_fixes']:,}")
    print(f"Window fixes: {diagnostics['window_fixes']:,} across {len(months)} months")
    print(
        "Hardware Adaptation: "
        f"rho={hardware['pooled_spearman_rho']:.3f}, "
        f"rho_adj={hardware['adjusted_spearman_rho']:.3f}, "
        f"slopes={hardware['pooled_slope_pp_per_year']:.1f}/"
        f"{hardware['adjusted_slope_pp_per_year']:.1f} pp/year"
    )
    def display_path(path: Path) -> str:
        try:
            return str(path.resolve().relative_to(ROOT))
        except ValueError:
            return str(path.resolve())

    print(f"Wrote {display_path(results_path)}")
    print(f"Wrote {display_path(monthly_path)}")
    print(f"Wrote {display_path(project_monthly_path)}")
    print(f"Wrote {display_path(args.report)}")


if __name__ == "__main__":
    main()
