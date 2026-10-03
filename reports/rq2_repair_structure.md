# RQ2: Repair structure

This report is generated from the public repair-operation annotations and published derived file/function and patch measures.

## Repair operations

- Layer-specific repair-operation instances: **19,965**
- Logic Correction + Adaptation: **14,702 (73.6%)**

| Repair operation | Instances | Share |
|---|---:|---:|
| Logic Correction | 8,728 | 43.7% |
| Adaptation | 5,974 | 29.9% |
| Configuration | 1,263 | 6.3% |
| Validation | 1,289 | 6.5% |
| Reorganization | 1,072 | 5.4% |
| Recovery | 573 | 2.9% |
| Optimization | 497 | 2.5% |
| Synchronization | 391 | 2.0% |
| Allocation | 178 | 0.9% |

The full architectural-layer × repair-operation table is `results/repair_operation_counts.csv`.

## File and function concentration

| Scope | Entities | Weighted bug total | Top 20% coverage |
|---|---:|---:|---:|
| Files | 8,025 | 12,707.0 | 79.6% |
| Functions | 26,565 | 11,526.0 | 68.4% |

| Project | File top-20% coverage | Function top-20% coverage |
|---|---:|---:|
| llama.cpp | 85.1% | 69.4% |
| vLLM | 76.7% | 68.8% |
| DeepSpeed | 78.4% | 67.2% |
| MLC-LLM | 69.3% | 61.7% |
| TensorRT-LLM | 79.3% | 67.5% |
| TGI | 74.3% | 64.5% |

## Fix size

| Fixes | Median lines | P75 | P90 | P95 |
|---:|---:|---:|---:|---:|
| 12,707 | 14 | 52 | 165 | 326.7 |

| Modified-file bucket | Fixes | Median changed lines | P90 changed lines |
|---|---:|---:|---:|
| 1 file | 6,883 | 6 | 32 |
| 2-5 files | 4,672 | 35 | 179 |
| 6+ files | 1,152 | 213.5 | 1043.5 |

Complete upstream patches are not redistributed. The per-PR derived measures in `data/fix_size_stats.json` preserve the published quantities.
