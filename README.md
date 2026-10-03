# Understanding the Structure and Evolution of Bug Maintenance in LLM Inference Engines

This repository is the public artifact for our empirical study of bug
maintenance in six open-source LLM inference engines: llama.cpp, vLLM,
DeepSpeed, MLC-LLM, TensorRT-LLM, and Text Generation Inference (TGI).

The artifact contains 12,707 merged and manually validated bug-fixing pull
requests. It connects observable symptoms, faulty architectural layers, repair
operations, modified code entities, and temporal repair scope.

## Study at a glance

- 50,121 candidate bug-fixing pull requests were screened.
- 12,707 merged pull requests were retained as validated fixes.
- RQ1 studies symptom--architectural-layer associations.
- RQ2 studies repair operations and file/function concentration.
- RQ3 studies modified-file breadth and architectural composition over time.
- The formal RQ3 window contains 12,299 fixes across 39 months
  (January 2023--March 2026).

The public data export intentionally omits free-text PR descriptions, LLM
reasoning, complete code diffs, caches, and backups. These fields are not
needed to reproduce the reported statistics and may contain token-shaped text
copied from public issue reports. The retained fields and derived data are
documented in [`data/README.md`](data/README.md).

## Repository layout

```text
.
├── data/                  # Analysis-ready annotations and derived data
├── figures/               # Generated figures used for artifact inspection
├── paper/                 # Authoritative manuscript source and final PDF
├── reports/               # Human-readable current reports for RQ1--RQ3
├── results/               # Machine-readable tables and reproduced reports
├── scripts/               # Validation and reproduction scripts
├── CITATION.cff
├── REPOSITORY_CONTENTS.md # Exact public include/exclude policy
└── requirements.txt
```

Historical drafts, collection caches, full PR diffs, temporary compilation
files, cover letters, and third-party reference PDFs are not part of this
public artifact.

## Quick validation

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/validate_artifact.py
```

Expected validation anchors are:

```text
canonical fixes: 12,707
repair-operation instances: 19,965
Logic Correction + Adaptation instances: 14,702 (73.6%)
RQ3 window: 12,299 fixes, 39 months
```

After intentionally changing a published file, refresh the integrity manifest
with `python scripts/update_checksums.py`.

Generate all current RQ1--RQ3 reports and machine-readable summaries with:

```bash
python scripts/generate_reports.py
python scripts/generate_reports.py --check
```

## Reproducing the analyses

### RQ1: symptoms and architectural layers

```bash
python scripts/plot_symptom_distribution.py
python scripts/plot_rq1_symptom_layer.py
```

The scripts read the analysis-ready bug records and write figures to
`figures/generated/`. Each bug spanning `k` distinct architectural layers
contributes `1/k` to each layer, so every bug has total weight one.

### RQ2: repair structure

```bash
python scripts/plot_concentration_curves.py \
  --files-input data/pareto/bug_file_distribution_weighted_alpha0.8_by_project.json \
  --functions-input data/bug_function_distribution_weighted_alpha0.8_by_project.json \
  --files-output figures/generated/concentration_files.pdf \
  --functions-output figures/generated/concentration_functions.pdf
```

`results/repair_operation_counts.csv` is generated from the public
repair-operation annotations during release preparation. The paper counts one instance for every recorded
root-cause entry in the eight principal layers, excludes the residual `Other`
layer, and excludes 15 fixes assigned to rare residual operations.

The repository includes derived per-PR file/function weights rather than the
complete upstream patches. This reproduces the concentration analysis while
avoiding redistribution of a large code-diff archive.

### RQ3: repair evolution

```bash
python scripts/plot_file_breadth.py --variant single
python scripts/analyze_rq3_layer_trends.py \
  --output-dir results/rq3_layer_trends \
  --report results/rq3_layer_trends.md
```

The layer-trend script deterministically reproduces the 39 monthly shares,
fixed-project-weight standardization, Spearman correlations, 20,000 two-sided
permutations, Benjamini--Hochberg correction, and percentage-point slopes.

The corresponding human-readable reports are in [`reports/`](reports/).
They are regenerated from the public 12,707-fix corpus and published derived
data; superseded exploratory reports are intentionally excluded.

## Building the paper

The authoritative manuscript entry point is `paper/main.tex`.

```bash
cd paper
latexmk -g -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The checked-in PDF is provided for inspection. LaTeX auxiliary files are not
part of the repository.

## Interpretation boundaries

- The unit of analysis is a merged bug-fixing PR, not an issue.
- Monthly architectural shares are compositional and sum to 100%; a larger
  share does not establish that a layer became less reliable.
- Correlations describe observed bug-fixing activity and are not causal.
- The corpus covers public merged fixes in six projects and does not represent
  undiscovered, private, or unresolved defects.

## Citation

Please use the metadata in [`CITATION.cff`](CITATION.cff). Bibliographic venue,
year, DOI, and page information should be added after publication.

## License

A project license has deliberately not been selected in this preparation
step. The repository owners should add the intended code and data licenses
before making the artifact public.
