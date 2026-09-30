# MAAT experiment results

Generator: **ollama:llama3.1:8b**  ·  runs: 5

## Multi-seed summary (mean [95% CI])

| Config | C1 raw | C2 grounded | C3 validated | gated→review % | E3 caught % | False-block % |
|---|---|---|---|---|---|---|
| guide_train | 18.66 [15.32, 22.0] | 88.32 [85.36, 91.28] | 100.0 [100.0, 100.0] | 11.68 [8.72, 14.64] | 100.0 [100.0, 100.0] | 0.0 [0.0, 0.0] |

## E1 — harmonization coverage & schema validity

| Config | Seed | Alerts | Valid OCSF % | UNKNOWN field % |
|---|---|---|---|---|
| guide_train | 7 | 120 | 100.0 | 46.5 |
| guide_train | 11 | 120 | 100.0 | 47.7 |
| guide_train | 13 | 120 | 100.0 | 47.7 |
| guide_train | 17 | 120 | 100.0 | 45.4 |
| guide_train | 19 | 120 | 100.0 | 47.7 |

## E2 — faithfulness (emitted-clean rate)

_C3 emitted-clean is 100% by construction of the gate; the empirical quantities are C1, C2, and gated-to-review._

| Config | Seed | C1 raw | C2 grounded | C3 validated | gated→review % |
|---|---|---|---|---|---|
| guide_train | 7 | 15.0 | 90.0 | 100.0 | 10.0 |
| guide_train | 11 | 20.8 | 90.8 | 100.0 | 9.2 |
| guide_train | 13 | 15.8 | 88.3 | 100.0 | 11.7 |
| guide_train | 17 | 17.5 | 82.5 | 100.0 | 17.5 |
| guide_train | 19 | 24.2 | 90.0 | 100.0 | 10.0 |

## E3 — injection robustness

| Config | Seed | Poisoned | Caught % | False-block % |
|---|---|---|---|---|
| guide_train | 7 | 24 | 100.0 | 0.0 |
| guide_train | 11 | 24 | 100.0 | 0.0 |
| guide_train | 13 | 24 | 100.0 | 0.0 |
| guide_train | 17 | 24 | 100.0 | 0.0 |
| guide_train | 19 | 24 | 100.0 | 0.0 |

## Runtime (per alert; summarize timed on the single generation pass)

| Config | Seed | adapt ms | summarize ms | validate ms | validator overhead % |
|---|---|---|---|---|---|
| guide_train | 7 | 0.081 | 1745.087 | 0.102 | 0.0 |
| guide_train | 11 | 0.071 | 1588.61 | 0.102 | 0.0 |
| guide_train | 13 | 0.081 | 1549.634 | 0.097 | 0.0 |
| guide_train | 17 | 0.089 | 1553.296 | 0.102 | 0.0 |
| guide_train | 19 | 0.085 | 1641.344 | 0.092 | 0.0 |

## LLM-judge disagreement with the deterministic field-level checker

Judge = LLM-as-judge; Checker = deterministic field-level validator. The gate equals the checker by construction, so it is not a column.

| Config | Seed | Judge faithful, checker flags | Judge unfaithful, checker clean |
|---|---|---|---|
| guide_train | 7 | 11 | 11 |
| guide_train | 11 | 11 | 10 |
| guide_train | 13 | 12 | 11 |
| guide_train | 17 | 19 | 7 |
| guide_train | 19 | 9 | 6 |
