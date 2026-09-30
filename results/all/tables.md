### Table: Full-corpus harmonization (E1, deterministic)

Over the entire AIT-ADS reduced corpus: **2,655,821** alerts, **100.0%** valid OCSF.

| Detector | Alerts | Valid OCSF % | UNKNOWN field % |
|---|---:|---:|---:|
| wazuh | 2,293,628 | 100.0 | 75.0 |
| suricata | 306,635 | 100.0 | 75.0 |
| aminer | 55,558 | 100.0 | 75.0 |

### Table: Faithfulness and injection (mean [95% CI] over seeds)

_C3 emitted-clean and injection-caught are 100% by construction (gate definition; non-adaptive injection strings). The empirical quantities are C1, C2, gated-to-review, and false-block._

| Config | C1 raw | C2 grounded | C3 validated | Gated→review % | Injection caught % | False-block % |
|---|---|---|---|---|---|---|
| synthetic | 19.5 [16.29, 22.71] | 69.18 [67.54, 70.82] | 100.0 [100.0, 100.0] | 30.82 [29.18, 32.46] | 100.0 [100.0, 100.0] | 0.0 [0.0, 0.0] |
| ait_csv_pooled | 17.7 [14.76, 20.64] | 64.68 [59.44, 69.92] | 100.0 [100.0, 100.0] | 35.32 [30.08, 40.56] | 100.0 [100.0, 100.0] | 5.82 [0.93, 10.71] |
| guide_train | 16.5 [7.39, 25.61] | 78.0 [69.6, 86.4] | 100.0 [100.0, 100.0] | 22.0 [13.6, 30.4] | 100.0 [100.0, 100.0] | 0.0 [0.0, 0.0] |

### Table: Runtime per alert (mean [95% CI])

| Config | Summarize ms | Validate ms | Validator overhead % |
|---|---|---|---|
| synthetic | 919.43 [894.37, 944.48] | 0.12 [0.11, 0.12] | 0.0 [0.0, 0.0] |
| ait_csv_pooled | 1103.7 [1041.15, 1166.26] | 0.12 [0.11, 0.13] | 0.0 [0.0, 0.0] |
| guide_train | 829.96 [801.72, 858.2] | 0.12 [0.11, 0.13] | 0.0 [0.0, 0.0] |

### Table: LLM-judge disagreement with the deterministic checker (totals over seeds)

Judge = LLM-as-judge; Checker = deterministic field-level validator. The gate equals the checker by construction, so it is not a column.

| Config | Judge faithful, checker flags | Judge unfaithful, checker clean |
|---|---:|---:|
| synthetic | 66 | 276 |
| ait_csv_pooled | 92 | 252 |
| guide_train | 10 | 115 |

