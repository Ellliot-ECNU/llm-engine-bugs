# RQ1: Failure localization

This report is generated from the public 12,707-fix corpus by `scripts/generate_reports.py`.
Each fix has one normalized symptom. Distinct architectural layers receive `1/k` weight, so every fix contributes total weight one.

## Corpus anchors

- Canonical fixes: **12,707**
- Incorrect output, runtime crash, and model-loading fixes: **4,001 (31.5%)**

## Symptom distribution

| Symptom | Fixes | Share |
|---|---:|---:|
| API/argument parsing Error | 2,845 | 22.4% |
| Incorrect/Inaccuracy Output | 2,271 | 17.9% |
| Performance/Memory Issue | 1,857 | 14.6% |
| Build/Compilation Error | 1,837 | 14.5% |
| Hardware/Backend Compatibility Issue | 1,239 | 9.8% |
| Runtime Crash | 1,154 | 9.1% |
| Model Loading Error | 576 | 4.5% |
| Distributed Parallelism/Sharding Bug | 545 | 4.3% |
| Other | 271 | 2.1% |
| Security Vulnerability | 112 | 0.9% |

## Project profiles

| Project | Fixes | Leading symptom | Leading share | Top-three share |
|---|---:|---|---:|---:|
| llama.cpp | 3,004 | Incorrect/Inaccuracy Output | 20.9% | 59.2% |
| vLLM | 5,915 | API/argument parsing Error | 24.0% | 54.1% |
| DeepSpeed | 1,118 | API/argument parsing Error | 21.9% | 52.5% |
| MLC-LLM | 487 | API/argument parsing Error | 27.7% | 70.0% |
| TensorRT-LLM | 1,784 | Performance/Memory Issue | 25.2% | 64.0% |
| TGI | 399 | API/argument parsing Error | 30.1% | 62.9% |

## Weighted architectural-layer totals

| Architectural layer | Weighted fixes | Share |
|---|---:|---:|
| Scheduler/Runtime | 4,887.8 | 38.5% |
| Hardware Adaptation | 2,123.0 | 16.7% |
| Operators/Backend | 1,660.2 | 13.1% |
| Config/Entrypoint | 1,276.3 | 10.0% |
| Tests/Bench | 1,151.7 | 9.1% |
| Other | 571.8 | 4.5% |
| Compiler/Optimization | 432.0 | 3.4% |
| Build/Release | 399.3 | 3.1% |
| Docs | 204.8 | 1.6% |

## Selected symptom-layer associations reported in the paper

| Architectural layer | Symptom | Weighted association | Layer total | Within-layer share | Lift |
|---|---|---:|---:|---:|---:|
| Build/Release | Build/Compilation Error | 344.0 | 399.3 | 86.1% | 5.96 |
| Config/Entrypoint | API/argument parsing Error | 677.0 | 1276.3 | 53.0% | 2.37 |
| Hardware Adaptation | Hardware/Backend Compatibility Issue | 411.8 | 2123.0 | 19.4% | 1.99 |

Figures are available under `figures/generated/` and the exact manuscript figures under `paper/fig/`.
Lift is descriptive association, not causal evidence or a measured localization success rate.
