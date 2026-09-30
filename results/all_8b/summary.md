# MAAT experiment results

Generator: **ollama:llama3.1:8b**  ·  runs: 15

## Multi-seed summary (mean [95% CI])

| Config | C1 raw | C2 grounded | C3 validated | gated→review % | E3 caught % | False-block % |
|---|---|---|---|---|---|---|
| synthetic | 19.5 [16.29, 22.71] | 94.98 [93.42, 96.54] | 100.0 [100.0, 100.0] | 5.02 [3.46, 6.58] | 100.0 [100.0, 100.0] | 0.0 [0.0, 0.0] |
| ait_csv_pooled | 17.7 [14.76, 20.64] | 92.02 [87.45, 96.59] | 100.0 [100.0, 100.0] | 7.98 [3.41, 12.55] | 100.0 [100.0, 100.0] | 5.82 [0.93, 10.71] |
| guide_train | 16.5 [7.39, 25.61] | 88.0 [83.0, 93.0] | 100.0 [100.0, 100.0] | 12.0 [7.0, 17.0] | 100.0 [100.0, 100.0] | 0.0 [0.0, 0.0] |

## E1 — harmonization coverage & schema validity

| Config | Seed | Alerts | Valid OCSF % | UNKNOWN field % |
|---|---|---|---|---|
| synthetic | 7 | 120 | 100.0 | 33.3 |
| ait_csv_pooled | 7 | 120 | 100.0 | 75.0 |
| guide_train | 7 | 40 | 100.0 | 46.9 |
| synthetic | 11 | 120 | 100.0 | 33.3 |
| ait_csv_pooled | 11 | 120 | 100.0 | 75.0 |
| guide_train | 11 | 40 | 100.0 | 48.1 |
| synthetic | 13 | 120 | 100.0 | 33.3 |
| ait_csv_pooled | 13 | 120 | 100.0 | 75.0 |
| guide_train | 13 | 40 | 100.0 | 47.5 |
| synthetic | 17 | 120 | 100.0 | 33.3 |
| ait_csv_pooled | 17 | 120 | 100.0 | 75.0 |
| guide_train | 17 | 40 | 100.0 | 47.5 |
| synthetic | 19 | 120 | 100.0 | 33.3 |
| ait_csv_pooled | 19 | 120 | 100.0 | 75.0 |
| guide_train | 19 | 40 | 100.0 | 44.4 |

## E2 — faithfulness (emitted-clean rate)

_C3 emitted-clean is 100% by construction of the gate; the empirical quantities are C1, C2, and gated-to-review._

| Config | Seed | C1 raw | C2 grounded | C3 validated | gated→review % |
|---|---|---|---|---|---|
| synthetic | 7 | 14.2 | 97.5 | 100.0 | 2.5 |
| ait_csv_pooled | 7 | 14.2 | 89.2 | 100.0 | 10.8 |
| guide_train | 7 | 7.5 | 90.0 | 100.0 | 10.0 |
| synthetic | 11 | 20.8 | 95.8 | 100.0 | 4.2 |
| ait_csv_pooled | 11 | 19.2 | 95.0 | 100.0 | 5.0 |
| guide_train | 11 | 17.5 | 95.0 | 100.0 | 5.0 |
| synthetic | 13 | 18.3 | 93.3 | 100.0 | 6.7 |
| ait_csv_pooled | 13 | 14.2 | 96.7 | 100.0 | 3.3 |
| guide_train | 13 | 5.0 | 90.0 | 100.0 | 10.0 |
| synthetic | 17 | 20.0 | 95.0 | 100.0 | 5.0 |
| ait_csv_pooled | 17 | 19.2 | 95.0 | 100.0 | 5.0 |
| guide_train | 17 | 30.0 | 80.0 | 100.0 | 20.0 |
| synthetic | 19 | 24.2 | 93.3 | 100.0 | 6.7 |
| ait_csv_pooled | 19 | 21.7 | 84.2 | 100.0 | 15.8 |
| guide_train | 19 | 22.5 | 85.0 | 100.0 | 15.0 |

## E3 — injection robustness

| Config | Seed | Poisoned | Caught % | False-block % |
|---|---|---|---|---|
| synthetic | 7 | 24 | 100.0 | 0.0 |
| ait_csv_pooled | 7 | 24 | 100.0 | 12.5 |
| guide_train | 7 | 24 | 100.0 | 0.0 |
| synthetic | 11 | 24 | 100.0 | 0.0 |
| ait_csv_pooled | 11 | 24 | 100.0 | 0.0 |
| guide_train | 11 | 24 | 100.0 | 0.0 |
| synthetic | 13 | 24 | 100.0 | 0.0 |
| ait_csv_pooled | 13 | 24 | 100.0 | 0.0 |
| guide_train | 13 | 24 | 100.0 | 0.0 |
| synthetic | 17 | 24 | 100.0 | 0.0 |
| ait_csv_pooled | 17 | 24 | 100.0 | 8.3 |
| guide_train | 17 | 24 | 100.0 | 0.0 |
| synthetic | 19 | 24 | 100.0 | 0.0 |
| ait_csv_pooled | 19 | 24 | 100.0 | 8.3 |
| guide_train | 19 | 24 | 100.0 | 0.0 |

## Runtime (per alert; summarize timed on the single generation pass)

| Config | Seed | adapt ms | summarize ms | validate ms | validator overhead % |
|---|---|---|---|---|---|
| synthetic | 7 | 0.025 | 1787.15 | 0.035 | 0.0 |
| ait_csv_pooled | 7 | 0.054 | 2128.638 | 0.086 | 0.0 |
| guide_train | 7 | 0.065 | 1447.834 | 0.092 | 0.0 |
| synthetic | 11 | 0.095 | 2145.566 | 0.116 | 0.0 |
| ait_csv_pooled | 11 | 0.076 | 1961.062 | 0.109 | 0.0 |
| guide_train | 11 | 0.07 | 1396.089 | 0.09 | 0.0 |
| synthetic | 13 | 0.09 | 2237.848 | 0.107 | 0.0 |
| ait_csv_pooled | 13 | 0.074 | 2053.178 | 0.113 | 0.0 |
| guide_train | 13 | 0.064 | 1428.428 | 0.087 | 0.0 |
| synthetic | 17 | 0.085 | 2347.702 | 0.113 | 0.0 |
| ait_csv_pooled | 17 | 0.075 | 2090.372 | 0.105 | 0.0 |
| guide_train | 17 | 0.062 | 1482.15 | 0.085 | 0.0 |
| synthetic | 19 | 0.081 | 2231.134 | 0.103 | 0.0 |
| ait_csv_pooled | 19 | 0.067 | 2079.336 | 0.104 | 0.0 |
| guide_train | 19 | 0.071 | 1482.487 | 0.097 | 0.0 |

## LLM-judge disagreement with the deterministic field-level checker

Judge = LLM-as-judge; Checker = deterministic field-level validator. The gate equals the checker by construction, so it is not a column.

| Config | Seed | Judge faithful, checker flags | Judge unfaithful, checker clean |
|---|---|---|---|
| synthetic | 7 | 3 | 10 |
| ait_csv_pooled | 7 | 11 | 11 |
| guide_train | 7 | 4 | 6 |
| synthetic | 11 | 3 | 2 |
| ait_csv_pooled | 11 | 6 | 17 |
| guide_train | 11 | 2 | 4 |
| synthetic | 13 | 7 | 9 |
| ait_csv_pooled | 13 | 3 | 14 |
| guide_train | 13 | 4 | 0 |
| synthetic | 17 | 5 | 10 |
| ait_csv_pooled | 17 | 6 | 9 |
| guide_train | 17 | 7 | 5 |
| synthetic | 19 | 7 | 8 |
| ait_csv_pooled | 19 | 19 | 11 |
| guide_train | 19 | 6 | 2 |
