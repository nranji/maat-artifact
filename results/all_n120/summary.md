# MAAT experiment results

Generator: **ollama:llama3.2:3b**  ·  runs: 15

## Multi-seed summary (mean [95% CI])

| Config | C1 raw | C2 grounded | C3 validated | gated→review % | E3 caught % | False-block % |
|---|---|---|---|---|---|---|
| synthetic | 19.6 [17.17, 22.03] | 68.16 [67.45, 68.87] | 100.0 [100.0, 100.0] | 31.84 [31.13, 32.55] | 100.0 [100.0, 100.0] | 0.0 [0.0, 0.0] |
| ait_csv_pooled | 18.84 [15.89, 21.79] | 66.5 [64.51, 68.49] | 100.0 [100.0, 100.0] | 33.5 [31.51, 35.49] | 100.0 [100.0, 100.0] | 2.52 [0.5, 4.54] |
| guide_train | 18.66 [15.32, 22.0] | 79.34 [76.73, 81.95] | 100.0 [100.0, 100.0] | 20.66 [18.05, 23.27] | 100.0 [100.0, 100.0] | 0.0 [0.0, 0.0] |

## E1 — harmonization coverage & schema validity

| Config | Seed | Alerts | Valid OCSF % | UNKNOWN field % |
|---|---|---|---|---|
| synthetic | 7 | 360 | 100.0 | 33.3 |
| ait_csv_pooled | 7 | 360 | 100.0 | 75.0 |
| guide_train | 7 | 120 | 100.0 | 46.5 |
| synthetic | 11 | 360 | 100.0 | 33.3 |
| ait_csv_pooled | 11 | 360 | 100.0 | 75.0 |
| guide_train | 11 | 120 | 100.0 | 47.7 |
| synthetic | 13 | 360 | 100.0 | 33.3 |
| ait_csv_pooled | 13 | 360 | 100.0 | 75.0 |
| guide_train | 13 | 120 | 100.0 | 47.7 |
| synthetic | 17 | 360 | 100.0 | 33.3 |
| ait_csv_pooled | 17 | 360 | 100.0 | 75.0 |
| guide_train | 17 | 120 | 100.0 | 45.4 |
| synthetic | 19 | 360 | 100.0 | 33.3 |
| ait_csv_pooled | 19 | 360 | 100.0 | 75.0 |
| guide_train | 19 | 120 | 100.0 | 47.7 |

## E2 — faithfulness (emitted-clean rate)

_C3 emitted-clean is 100% by construction of the gate; the empirical quantities are C1, C2, and gated-to-review._

| Config | Seed | C1 raw | C2 grounded | C3 validated | gated→review % |
|---|---|---|---|---|---|
| synthetic | 7 | 18.3 | 69.2 | 100.0 | 30.8 |
| ait_csv_pooled | 7 | 17.8 | 65.3 | 100.0 | 34.7 |
| guide_train | 7 | 15.0 | 75.0 | 100.0 | 25.0 |
| synthetic | 11 | 23.3 | 68.3 | 100.0 | 31.7 |
| ait_csv_pooled | 11 | 23.1 | 66.9 | 100.0 | 33.1 |
| guide_train | 11 | 20.8 | 81.7 | 100.0 | 18.3 |
| synthetic | 13 | 15.8 | 67.5 | 100.0 | 32.5 |
| ait_csv_pooled | 13 | 13.9 | 70.3 | 100.0 | 29.7 |
| guide_train | 13 | 15.8 | 80.8 | 100.0 | 19.2 |
| synthetic | 17 | 20.3 | 67.2 | 100.0 | 32.8 |
| ait_csv_pooled | 17 | 19.4 | 65.0 | 100.0 | 35.0 |
| guide_train | 17 | 17.5 | 77.5 | 100.0 | 22.5 |
| synthetic | 19 | 20.3 | 68.6 | 100.0 | 31.4 |
| ait_csv_pooled | 19 | 20.0 | 65.0 | 100.0 | 35.0 |
| guide_train | 19 | 24.2 | 81.7 | 100.0 | 18.3 |

## E3 — injection robustness

| Config | Seed | Poisoned | Caught % | False-block % |
|---|---|---|---|---|
| synthetic | 7 | 24 | 100.0 | 0.0 |
| ait_csv_pooled | 7 | 24 | 100.0 | 0.0 |
| guide_train | 7 | 24 | 100.0 | 0.0 |
| synthetic | 11 | 24 | 100.0 | 0.0 |
| ait_csv_pooled | 11 | 24 | 100.0 | 4.2 |
| guide_train | 11 | 24 | 100.0 | 0.0 |
| synthetic | 13 | 24 | 100.0 | 0.0 |
| ait_csv_pooled | 13 | 24 | 100.0 | 0.0 |
| guide_train | 13 | 24 | 100.0 | 0.0 |
| synthetic | 17 | 24 | 100.0 | 0.0 |
| ait_csv_pooled | 17 | 24 | 100.0 | 4.2 |
| guide_train | 17 | 24 | 100.0 | 0.0 |
| synthetic | 19 | 24 | 100.0 | 0.0 |
| ait_csv_pooled | 19 | 24 | 100.0 | 4.2 |
| guide_train | 19 | 24 | 100.0 | 0.0 |

## Runtime (per alert; summarize timed on the single generation pass)

| Config | Seed | adapt ms | summarize ms | validate ms | validator overhead % |
|---|---|---|---|---|---|
| synthetic | 7 | 0.086 | 1012.33 | 0.124 | 0.0 |
| ait_csv_pooled | 7 | 0.065 | 1011.933 | 0.107 | 0.0 |
| guide_train | 7 | 0.061 | 857.581 | 0.092 | 0.0 |
| synthetic | 11 | 0.084 | 1058.882 | 0.109 | 0.0 |
| ait_csv_pooled | 11 | 0.068 | 960.415 | 0.111 | 0.0 |
| guide_train | 11 | 0.065 | 823.128 | 0.1 | 0.0 |
| synthetic | 13 | 0.085 | 1087.465 | 0.112 | 0.0 |
| ait_csv_pooled | 13 | 0.069 | 991.296 | 0.11 | 0.0 |
| guide_train | 13 | 0.061 | 844.109 | 0.09 | 0.0 |
| synthetic | 17 | 0.072 | 1040.685 | 0.1 | 0.0 |
| ait_csv_pooled | 17 | 0.063 | 936.683 | 0.106 | 0.0 |
| guide_train | 17 | 0.069 | 809.7 | 0.103 | 0.0 |
| synthetic | 19 | 0.082 | 1059.329 | 0.104 | 0.0 |
| ait_csv_pooled | 19 | 0.067 | 980.809 | 0.111 | 0.0 |
| guide_train | 19 | 0.075 | 820.868 | 0.128 | 0.0 |

## LLM-judge disagreement with the deterministic field-level checker

Judge = LLM-as-judge; Checker = deterministic field-level validator. The gate equals the checker by construction, so it is not a column.

| Config | Seed | Judge faithful, checker flags | Judge unfaithful, checker clean |
|---|---|---|---|
| synthetic | 7 | 29 | 170 |
| ait_csv_pooled | 7 | 49 | 146 |
| guide_train | 7 | 10 | 69 |
| synthetic | 11 | 47 | 152 |
| ait_csv_pooled | 11 | 42 | 141 |
| guide_train | 11 | 5 | 73 |
| synthetic | 13 | 32 | 154 |
| ait_csv_pooled | 13 | 45 | 148 |
| guide_train | 13 | 7 | 71 |
| synthetic | 17 | 37 | 168 |
| ait_csv_pooled | 17 | 39 | 157 |
| guide_train | 17 | 6 | 63 |
| synthetic | 19 | 33 | 164 |
| ait_csv_pooled | 19 | 51 | 145 |
| guide_train | 19 | 4 | 75 |
