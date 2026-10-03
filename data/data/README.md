# Data description

## Analysis-ready records

`final_bug_results_with_root_cause_completed_symptom.json` is a JSON object
keyed by the public GitHub pull-request URL. It contains exactly 12,707 records.

Each record retains only fields used by the paper:

- `title`: public PR title;
- `is_bug_related`, `status`, `pr_status`: corpus eligibility fields;
- `symptom`: one primary observable symptom;
- `root_causes`: one or more objects with `file`, `function`, and manually
  assigned architectural `layer`;
- `root_cause_layers`: a convenience list retained for compatibility. Analyses
  should prefer `root_causes[].layer` because it is the manually saved source.

Free-text descriptions and LLM reasoning are intentionally excluded.

`bug_timestamps.json` maps the same 12,707 PR URLs to creation timestamps.

`final_bug_results_with_root_cause_completed_symptom_fixed_merged_fix_pattern.json`
adds `fix_pattern_analysis` with the repair operation and compact supporting
fields. The operation named `Correction` in the data is reported as
`Logic Correction` in the paper.

## Counting rules

- RQ1/RQ3: deduplicate the assigned layers for a bug; a bug spanning `k`
  layers contributes `1/k` to each layer.
- RQ2 repair-operation table: count every recorded root-cause entry in the
  eight principal layers. Exclude `Other` layer entries and the 15 fixes using
  rare residual operations. This yields 19,965 instances.
- RQ3: use PR creation month and the inclusive window 2023-01--2026-03.

## Derived data

- `pareto/bug_file_distribution_weighted_alpha0.8_by_project.json`: project
  file weights used for concentration curves.
- `pareto/bug_file_weights_per_issue_alpha0.8.json`: per-PR file weights.
- `bug_function_distribution_weighted_alpha0.8_by_project.json`: project
  function weights used for concentration curves.
- `bug_function_weights_per_issue_alpha0.8.json`: per-PR function weights.
- `fix_size_stats.json`: per-PR changed-line and modified-file measures.
- `monthly_file_bucket_counts.json`: monthly 1-file, 2--5-file, and 6+-file
  counts and shares.

Complete upstream patches are not redistributed. The derived records preserve
the quantities required for the published analyses.

Provider-key-shaped literals copied from upstream function identifiers are
replaced with explicit redaction markers. Their associated numeric weights and
PR mappings are unchanged, so the concentration results are unaffected.
