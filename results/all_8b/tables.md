### Table: Faithfulness and injection (mean [95% CI] over seeds)

_C3 emitted-clean and injection-caught are 100% by construction (gate definition; non-adaptive injection strings). The empirical quantities are C1, C2, gated-to-review, and false-block._

| Config | C1 raw | C2 grounded | C3 validated | Gated→review % | Injection caught % | False-block % |
|---|---|---|---|---|---|---|
| synthetic | 19.5 [16.29, 22.71] | 94.98 [93.42, 96.54] | 100.0 [100.0, 100.0] | 5.02 [3.46, 6.58] | 100.0 [100.0, 100.0] | 0.0 [0.0, 0.0] |
| ait_csv_pooled | 17.7 [14.76, 20.64] | 92.02 [87.45, 96.59] | 100.0 [100.0, 100.0] | 7.98 [3.41, 12.55] | 100.0 [100.0, 100.0] | 5.82 [0.93, 10.71] |
| guide_train | 16.5 [7.39, 25.61] | 88.0 [83.0, 93.0] | 100.0 [100.0, 100.0] | 12.0 [7.0, 17.0] | 100.0 [100.0, 100.0] | 0.0 [0.0, 0.0] |

### Table: Runtime per alert (mean [95% CI])

| Config | Summarize ms | Validate ms | Validator overhead % |
|---|---|---|---|
| synthetic | 2149.88 [1961.34, 2338.42] | 0.09 [0.07, 0.12] | 0.0 [0.0, 0.0] |
| ait_csv_pooled | 2062.52 [2007.41, 2117.63] | 0.1 [0.09, 0.11] | 0.0 [0.0, 0.0] |
| guide_train | 1447.4 [1415.1, 1479.7] | 0.09 [0.09, 0.09] | 0.0 [0.0, 0.0] |

### Table: LLM-judge disagreement with the deterministic checker (totals over seeds)

Judge = LLM-as-judge; Checker = deterministic field-level validator. The gate equals the checker by construction, so it is not a column.

| Config | Judge faithful, checker flags | Judge unfaithful, checker clean |
|---|---:|---:|
| synthetic | 25 | 39 |
| ait_csv_pooled | 45 | 62 |
| guide_train | 23 | 17 |

