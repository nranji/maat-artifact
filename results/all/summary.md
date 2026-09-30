# MAAT experiment results

Generator: **ollama:llama3.2:3b**  ·  runs: 15

## E1-full — full-corpus OCSF validity (deterministic, no LLM)

Alerts: **2,655,821**  ·  Valid OCSF: **100.0%**  ·  UNKNOWN field rate: 75.0%

| Detector | n | Valid % | UNKNOWN field % |
|---|---|---|---|
| wazuh | 2,293,628 | 100.0 | 75.0 |
| suricata | 306,635 | 100.0 | 75.0 |
| aminer | 55,558 | 100.0 | 75.0 |

## Multi-seed summary (mean [95% CI])

| Config | C1 raw | C2 grounded | C3 validated | gated→review % | E3 caught % | False-block % |
|---|---|---|---|---|---|---|
| synthetic | 19.5 [16.29, 22.71] | 69.18 [67.54, 70.82] | 100.0 [100.0, 100.0] | 30.82 [29.18, 32.46] | 100.0 [100.0, 100.0] | 0.0 [0.0, 0.0] |
| ait_csv_pooled | 17.7 [14.76, 20.64] | 64.68 [59.44, 69.92] | 100.0 [100.0, 100.0] | 35.32 [30.08, 40.56] | 100.0 [100.0, 100.0] | 5.82 [0.93, 10.71] |
| guide_train | 16.5 [7.39, 25.61] | 78.0 [69.6, 86.4] | 100.0 [100.0, 100.0] | 22.0 [13.6, 30.4] | 100.0 [100.0, 100.0] | 0.0 [0.0, 0.0] |

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

| Config | Seed | C1 raw | C2 grounded | C3 validated | gated→review % |
|---|---|---|---|---|---|
| synthetic | 7 | 14.2 | 70.0 | 100.0 | 30.0 |
| ait_csv_pooled | 7 | 14.2 | 66.7 | 100.0 | 33.3 |
| guide_train | 7 | 7.5 | 77.5 | 100.0 | 22.5 |
| synthetic | 11 | 20.8 | 71.7 | 100.0 | 28.3 |
| ait_csv_pooled | 11 | 19.2 | 57.5 | 100.0 | 42.5 |
| guide_train | 11 | 17.5 | 70.0 | 100.0 | 30.0 |
| synthetic | 13 | 18.3 | 68.3 | 100.0 | 31.7 |
| ait_csv_pooled | 13 | 14.2 | 66.7 | 100.0 | 33.3 |
| guide_train | 13 | 5.0 | 67.5 | 100.0 | 32.5 |
| synthetic | 17 | 20.0 | 69.2 | 100.0 | 30.8 |
| ait_csv_pooled | 17 | 19.2 | 60.0 | 100.0 | 40.0 |
| guide_train | 17 | 30.0 | 85.0 | 100.0 | 15.0 |
| synthetic | 19 | 24.2 | 66.7 | 100.0 | 33.3 |
| ait_csv_pooled | 19 | 21.7 | 72.5 | 100.0 | 27.5 |
| guide_train | 19 | 22.5 | 90.0 | 100.0 | 10.0 |

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
| synthetic | 7 | 0.078 | 919.635 | 0.111 | 0.0 |
| ait_csv_pooled | 7 | 0.073 | 1117.176 | 0.127 | 0.0 |
| guide_train | 7 | 0.079 | 809.158 | 0.121 | 0.0 |
| synthetic | 11 | 0.092 | 912.463 | 0.12 | 0.0 |
| ait_csv_pooled | 11 | 0.076 | 1105.017 | 0.126 | 0.0 |
| guide_train | 11 | 0.076 | 879.515 | 0.12 | 0.0 |
| synthetic | 13 | 0.083 | 884.89 | 0.119 | 0.0 |
| ait_csv_pooled | 13 | 0.077 | 1196.95 | 0.116 | 0.0 |
| guide_train | 13 | 0.087 | 816.296 | 0.137 | 0.0 |
| synthetic | 17 | 0.087 | 964.311 | 0.125 | 0.0 |
| ait_csv_pooled | 17 | 0.072 | 1102.885 | 0.111 | 0.0 |
| guide_train | 17 | 0.071 | 800.477 | 0.105 | 0.0 |
| synthetic | 19 | 0.081 | 915.829 | 0.12 | 0.0 |
| ait_csv_pooled | 19 | 0.076 | 996.491 | 0.126 | 0.0 |
| guide_train | 19 | 0.092 | 844.37 | 0.12 | 0.0 |

## Deterministic gate vs LLM-judge (same grounded summaries)

| Config | Seed | Det. leaked-unfaithful | Judge leaked-unfaithful | Det. over-blocked | Judge over-blocked |
|---|---|---|---|---|---|
| synthetic | 7 | 0 | 9 | 0 | 53 |
| ait_csv_pooled | 7 | 0 | 17 | 0 | 49 |
| guide_train | 7 | 0 | 5 | 0 | 22 |
| synthetic | 11 | 0 | 12 | 0 | 53 |
| ait_csv_pooled | 11 | 0 | 22 | 0 | 48 |
| guide_train | 11 | 0 | 3 | 0 | 17 |
| synthetic | 13 | 0 | 14 | 0 | 56 |
| ait_csv_pooled | 13 | 0 | 17 | 0 | 47 |
| guide_train | 13 | 0 | 0 | 0 | 17 |
| synthetic | 17 | 0 | 16 | 0 | 56 |
| ait_csv_pooled | 17 | 0 | 25 | 0 | 49 |
| guide_train | 17 | 0 | 1 | 0 | 29 |
| synthetic | 19 | 0 | 15 | 0 | 58 |
| ait_csv_pooled | 19 | 0 | 11 | 0 | 59 |
| guide_train | 19 | 0 | 1 | 0 | 30 |
