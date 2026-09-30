# Variance decomposition (ollama:llama3.2:3b, k=5)

Between-generation SD: k independent summaries on one fixed sample (seed 7). Between-seed SD: transcribed from the committed five-seed aggregates (AIT from results/all, GUIDE from results/all_n120).

Wall-clock: 1313.0s

| Corpus | n alerts | between-gen SD C2 | between-seed SD C2 | between-gen SD gated | between-seed SD gated |
|---|---:|---:|---:|---:|---:|
| ait_csv_pooled | 120 | 3.0827 | 5.97 | 3.0827 | 5.97 |
| guide_train | 120 | 2.4269 | 2.98 | 2.4269 | 2.98 |

