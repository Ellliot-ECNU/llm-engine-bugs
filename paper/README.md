# Manuscript source

`main.tex` is the authoritative entry point. Files under `sections/`, `Table/`,
and `fig/` are the exact sources referenced by it. Historical drafts, third-
party reference PDFs, and LaTeX auxiliary files are intentionally excluded.

Build with:

```bash
latexmk -g -pdf -interaction=nonstopmode -halt-on-error main.tex
```

After any source change, inspect undefined references/citations, overfull
boxes, figure rendering, table/figure placement, and the final page balance.

