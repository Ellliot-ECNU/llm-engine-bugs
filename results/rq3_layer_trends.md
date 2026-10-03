# Canonical RQ3 architectural-composition trends

- Period: **2023-01 to 2026-03** (39 months)
- Included fixes: **12,299**
- Weighting: distinct layers, **1/k per layer and bug**
- Permutation test: **20,000** two-sided permutations, seed **2026**
- Window summaries: equal-weight means of the first and last **12 monthly shares**

## Layer trends

| Layer | First 12m | Last 12m | Delta pp | rho | p | q | rho adjusted | Pooled pp/year | Adjusted pp/year |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Hardware Adaptation | 6.443% | 23.656% | +17.214 | 0.780910 | 4.99975e-05 | 8.99955e-05 | 0.739410 | +7.2562 | +6.6134 |
| Tests/Bench | 3.219% | 12.481% | +9.262 | 0.821803 | 4.99975e-05 | 8.99955e-05 | 0.675101 | +3.7493 | +2.6081 |
| Config/Entrypoint | 4.875% | 10.420% | +5.546 | 0.564199 | 0.000249988 | 0.000321413 | 0.238878 | +2.6598 | +1.3158 |
| Compiler/Optimization | 2.071% | 4.040% | +1.969 | 0.524557 | 0.00039998 | 0.000449978 | 0.443342 | +0.9771 | +1.0112 |
| Scheduler/Runtime | 44.088% | 33.587% | -10.501 | -0.381984 | 0.0170491 | 0.0170491 | -0.668421 | -4.0612 | -9.3680 |
| Docs | 2.823% | 1.115% | -1.708 | -0.576316 | 9.9995e-05 | 0.000149993 | -0.154453 | -0.8748 | -0.3629 |
| Operators/Backend | 22.449% | 9.106% | -13.343 | -0.653644 | 4.99975e-05 | 8.99955e-05 | -0.155668 | -6.0205 | -0.0726 |
| Other | 6.825% | 3.697% | -3.128 | -0.669636 | 4.99975e-05 | 8.99955e-05 | -0.137247 | -1.4937 | -0.2866 |
| Build/Release | 7.208% | 1.898% | -5.310 | -0.789069 | 4.99975e-05 | 8.99955e-05 | -0.644939 | -2.1923 | -1.4585 |

`First 12m` and `Last 12m` are means of monthly shares. Delta is computed from unrounded values. Pooled and adjusted slopes are least-squares percentage-point changes per year.

## Fixed project weights

| Project | Fixes | Weight |
|---|---:|---:|
| DeepSpeed | 715 | 0.058135 |
| TensorRT-LLM | 1,784 | 0.145052 |
| llama.cpp | 3,004 | 0.244247 |
| MLC-LLM | 487 | 0.039597 |
| TGI | 394 | 0.032035 |
| vLLM | 5,915 | 0.480933 |

## Reproduction

```bash
python scripts/analyze_rq3_layer_trends.py
```

The JSON output records the input SHA-256 hashes, filtering rules, parameters, full-precision statistics, and per-project trends. CSV files contain the pooled/standardized monthly series and active project-month series.
