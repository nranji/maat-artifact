### Table: Faithfulness and injection (mean [95% CI] over seeds)

_C3 emitted-clean and injection-caught are 100% by construction (gate definition; non-adaptive injection strings). The empirical quantities are C1, C2, gated-to-review, and false-block._

| Config | C1 raw | C2 grounded | C3 validated | Gated→review % | Injection caught % | False-block % |
|---|---|---|---|---|---|---|
| guide_train | 18.66 [15.32, 22.0] | 88.32 [85.36, 91.28] | 100.0 [100.0, 100.0] | 11.68 [8.72, 14.64] | 100.0 [100.0, 100.0] | 0.0 [0.0, 0.0] |

### Table: Runtime per alert (mean [95% CI])

| Config | Summarize ms | Validate ms | Validator overhead % |
|---|---|---|---|
| guide_train | 1615.59 [1544.4, 1686.79] | 0.1 [0.1, 0.1] | 0.0 [0.0, 0.0] |

### Table: LLM-judge disagreement with the deterministic checker (totals over seeds)

Judge = LLM-as-judge; Checker = deterministic field-level validator. The gate equals the checker by construction, so it is not a column.

| Config | Judge faithful, checker flags | Judge unfaithful, checker clean |
|---|---:|---:|
| guide_train | 62 | 45 |

