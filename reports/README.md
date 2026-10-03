# Reproduced analysis reports

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
