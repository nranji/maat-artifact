### Table: Faithfulness and injection (mean [95% CI] over seeds)

_C3 emitted-clean and injection-caught are 100% by construction (gate definition; non-adaptive injection strings). The empirical quantities are C1, C2, gated-to-review, and false-block._

| Config | C1 raw | C2 grounded | C3 validated | Gated→review % | Injection caught % | False-block % |
|---|---|---|---|---|---|---|
| synthetic | 19.6 [17.17, 22.03] | 68.16 [67.45, 68.87] | 100.0 [100.0, 100.0] | 31.84 [31.13, 32.55] | 100.0 [100.0, 100.0] | 0.0 [0.0, 0.0] |
| ait_csv_pooled | 18.84 [15.89, 21.79] | 66.5 [64.51, 68.49] | 100.0 [100.0, 100.0] | 33.5 [31.51, 35.49] | 100.0 [100.0, 100.0] | 2.52 [0.5, 4.54] |
| guide_train | 18.66 [15.32, 22.0] | 79.34 [76.73, 81.95] | 100.0 [100.0, 100.0] | 20.66 [18.05, 23.27] | 100.0 [100.0, 100.0] | 0.0 [0.0, 0.0] |

### Table: Runtime per alert (mean [95% CI])

| Config | Summarize ms | Validate ms | Validator overhead % |
|---|---|---|---|
| synthetic | 1051.74 [1027.49, 1075.98] | 0.11 [0.1, 0.12] | 0.0 [0.0, 0.0] |
| ait_csv_pooled | 976.23 [950.91, 1001.54] | 0.11 [0.11, 0.11] | 0.0 [0.0, 0.0] |
| guide_train | 831.08 [814.12, 848.03] | 0.1 [0.09, 0.12] | 0.0 [0.0, 0.0] |

### Table: LLM-judge disagreement with the deterministic checker (totals over seeds)

Judge = LLM-as-judge; Checker = deterministic field-level validator. The gate equals the checker by construction, so it is not a column.

| Config | Judge faithful, checker flags | Judge unfaithful, checker clean |
|---|---:|---:|
| synthetic | 178 | 808 |
| ait_csv_pooled | 226 | 737 |
| guide_train | 32 | 351 |

