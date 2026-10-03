# RQ3: Repair evolution

The formal window contains **12,299 fixes across 39 months** (2023-01 to 2026-03).

## File-breadth endpoints

| Bucket | January 2023 | March 2026 |
|---|---:|---:|
| 1 file | 18 (56.3%) | 405 (47.1%) |
| 2-5 files | 10 (31.3%) | 359 (41.8%) |
| 6+ files | 4 (12.5%) | 95 (11.1%) |

## Architectural-composition trends

| Architectural layer | First 12m | Last 12m | Delta pp | Pooled rho | Adjusted rho | Pooled pp/year | Adjusted pp/year |
|---|---:|---:|---:|---:|---:|---:|---:|
| Hardware Adaptation | 6.4% | 23.7% | +17.2 | 0.781 | 0.739 | +7.3 | +6.6 |
| Tests/Bench | 3.2% | 12.5% | +9.3 | 0.822 | 0.675 | +3.7 | +2.6 |
| Config/Entrypoint | 4.9% | 10.4% | +5.5 | 0.564 | 0.239 | +2.7 | +1.3 |
| Compiler/Optimization | 2.1% | 4.0% | +2.0 | 0.525 | 0.443 | +1.0 | +1.0 |
| Scheduler/Runtime | 44.1% | 33.6% | -10.5 | -0.382 | -0.668 | -4.1 | -9.4 |
| Docs | 2.8% | 1.1% | -1.7 | -0.576 | -0.154 | -0.9 | -0.4 |
| Operators/Backend | 22.4% | 9.1% | -13.3 | -0.654 | -0.156 | -6.0 | -0.1 |
| Other | 6.8% | 3.7% | -3.1 | -0.670 | -0.137 | -1.5 | -0.3 |
| Build/Release | 7.2% | 1.9% | -5.3 | -0.789 | -0.645 | -2.2 | -1.5 |

Full-precision p-values, BH-adjusted q-values, monthly series, fixed project weights, and per-project trends are under `results/rq3_layer_trends/`.
Monthly layer shares are compositional and describe observed fixing activity; they do not establish causal changes in a layer's reliability.
