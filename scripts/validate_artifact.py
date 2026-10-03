#!/usr/bin/env python3
"""Validate the public artifact against the manuscript's anchor values."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from generate_reports import render_outputs


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BUGS = DATA / "final_bug_results_with_root_cause_completed_symptom.json"
TIMESTAMPS = DATA / "bug_timestamps.json"
OPERATIONS = DATA / "final_bug_results_with_root_cause_completed_symptom_fixed_merged_fix_pattern.json"
TOKEN_PATTERN = re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{8,}")
MAJOR_OPERATIONS = {
    "Correction",
    "Adaptation",
    "Configuration",
    "Validation",
    "Reorganization",
    "Recovery",
    "Optimization",
    "Synchronization",
    "Allocation",
}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def project(url: str) -> str:
    parts = url.split("/")
    return "/".join(parts[3:5])


def main() -> None:
    bugs = load(BUGS)
    timestamps = load(TIMESTAMPS)
    operations = load(OPERATIONS)

    assert len(bugs) == 12_707, len(bugs)
    assert len(timestamps) == 12_707, len(timestamps)
    assert len(operations) == 12_707, len(operations)
    assert set(bugs) == set(timestamps) == set(operations)
    assert len({project(url) for url in bugs}) == 6
    assert all(
        record.get("is_bug_related") is True
        and str(record.get("status", "")).lower() == "fixed"
        and str(record.get("pr_status", "")).lower() == "merged"
        for record in bugs.values()
    )
    assert all(
        {item.get("layer") for item in record.get("root_causes", []) if isinstance(item, dict) and item.get("layer")}
        == {layer for layer in record.get("root_cause_layers", []) if layer}
        for record in bugs.values()
    ), "root_cause_layers must mirror the canonical root_causes[].layer assignments"

    months = Counter(str(timestamps[url])[:7] for url in bugs if "2023-01" <= str(timestamps[url])[:7] <= "2026-03")
    assert sum(months.values()) == 12_299, sum(months.values())
    assert len(months) == 39, len(months)

    counts: Counter[tuple[str, str]] = Counter()
    for record in operations.values():
        operation = (record.get("fix_pattern_analysis") or {}).get("repair_pattern")
        if operation not in MAJOR_OPERATIONS:
            continue
        for root_cause in record.get("root_causes") or []:
            layer = root_cause.get("layer") if isinstance(root_cause, dict) else None
            if layer and layer != "Other":
                counts[(layer, operation)] += 1

    instances = sum(counts.values())
    dominant = sum(value for (layer, operation), value in counts.items() if operation in {"Correction", "Adaptation"})
    assert instances == 19_965, instances
    assert dominant == 14_702, dominant

    for path in (BUGS, TIMESTAMPS, OPERATIONS):
        assert TOKEN_PATTERN.search(path.read_text(encoding="utf-8")) is None, f"secret-like token in {path}"

    report_outputs = render_outputs()
    stale_reports = [
        path.relative_to(ROOT).as_posix()
        for path, expected in report_outputs.items()
        if not path.exists() or path.read_text(encoding="utf-8") != expected
    ]
    assert not stale_reports, "stale or missing generated reports: " + ", ".join(stale_reports)

    print("Artifact validation passed")
    print(f"  canonical fixes: {len(bugs):,}")
    print(f"  projects: {len({project(url) for url in bugs})}")
    print(f"  repair-operation instances: {instances:,}")
    print(f"  Logic Correction + Adaptation: {dominant:,} ({100 * dominant / instances:.1f}%)")
    print(f"  RQ3 window: {sum(months.values()):,} fixes across {len(months)} months")
    print(f"  generated reports/results: {len(report_outputs)} current files")


if __name__ == "__main__":
    main()
