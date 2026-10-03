# Published figures

`generated/` contains the public outputs used to inspect the RQ1--RQ3
analyses. The plotting commands are documented in the repository-level
`README.md`.

The exact figure files referenced by the checked-in manuscript are also kept
under `paper/fig/` so that `paper/main.tex` builds without copying files. For
the RQ1 lift heatmap and stacked symptom distribution, the copies under
`generated/rq1_symptom_layer/` are byte-identical to the manuscript figures.

Some plotting scripts can create additional exploratory PNG/PDF variants.
Those variants are not required to reproduce the reported paper findings and
are therefore not all checked in.
