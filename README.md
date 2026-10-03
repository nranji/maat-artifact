# MAAT: Deterministic Faithfulness Checks for LLM-Assisted Security Alert Triage

Anonymous artifact accompanying the SaTML 2027 submission.

This repository contains the harmonizer, gateways, deterministic validators
(schema and faithfulness), dataset loaders, evaluation harness, LLM-as-judge
baseline, adaptive-injection experiment, and the scoring script for the
human-labeled study reported in the paper.

## Contents

```
src/                  Python sources
  nlip_soc.py           deterministic faithfulness validator
  generators.py         summary generators + injection templates
  run_experiment.py     one-corpus/one-seed experiment
  run_all.py            multi-seed sweep + LLM-judge baseline
  run_adaptive_injection.py   adaptive-injection experiment
  run_dataset_checks.py       E1 full-corpus mapping/validity checks
  run_variance.py       between-generation vs between-seed variance
  make_label_sheet.py   blinded human-study sheet builder
  score_labels.py       Fleiss' kappa + gate confusion matrix
  make_tables.py        renders paper tables from consolidated.json
  baselines.py          LLM-as-judge implementation
  agent_*.py            LLM agent wrappers (harmonizer / analyst / gateway)
  nlip_transport.py     NLIP transport shim
  datasets/             AIT-ADS and GUIDE loaders
  paths.py              repo-root data/ and results/ locations

data/                 dataset download instructions (no data shipped)
results/              committed aggregates + human-study sheet
  all/                    3B AIT-ADS paper run; GUIDE here is n=40, not the paper table
  all_n120/               3B GUIDE paper run (n=120)
  all_8b/                 8B AIT-ADS paper run; GUIDE here is n=40
  all_8b_guide_n120/      8B GUIDE paper run (n=120)
  variance/               between-generation vs between-seed SDs
  labels/                 human-study sheet, key, guide
figures/              matplotlib scripts + committed fig_e2.pdf / fig_runtime.pdf
requirements.txt      pinned Python dependencies
setup_ollama.sh       optional Ollama installer for local LLMs
```

Loaders and writers use the repository root: datasets go in `data/`, outputs
go in `results/`. Run the commands below from that root.

## Reproducing the paper

1. Install dependencies:
   ```
   python3 -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Serve the two harmonizer models locally with Ollama:
   ```
   bash setup_ollama.sh          # installs Ollama and pulls llama3.2:3b and llama3.1:8b
   ```

3. Download AIT-ADS and GUIDE per the instructions in `data/DOWNLOAD_DATASETS.md`.
   Neither dataset is redistributed here. Place files at:
   `data/ait_ads/alerts_csv.zip` and `data/guide/GUIDE_Train.csv` (plus Test).

4. Run the E1 full-corpus mapping and OCSF-validity check:
   ```
   python src/run_dataset_checks.py --e1-full
   ```

5. 3B paper configuration. `--n` defaults to 40. The paper's GUIDE tables use 120.
   ```
   export MAAT_OLLAMA_MODEL=llama3.2:3b

   # AIT-ADS (and a GUIDE n=40 run that is not the paper table)
   python src/run_all.py --paper --seeds 7,11,13,17,19 --out all

   # GUIDE paper configuration
   python src/run_all.py --paper --seeds 7,11,13,17,19 --n 120 --out all_n120
   ```

6. 8B paper configuration:
   ```
   export MAAT_OLLAMA_MODEL=llama3.1:8b

   python src/run_all.py --paper --seeds 7,11,13,17,19 --out all_8b

   # GUIDE only. The committed directory does not include AIT or synthetic.
   python src/run_all.py --paper --no-ait --no-synthetic \
     --seeds 7,11,13,17,19 --n 120 --out all_8b_guide_n120
   ```

`results/all/` holds the AIT-ADS paper results and an earlier GUIDE `n=40` run.
The GUIDE values in the paper are in `results/all_n120/`. The 8B GUIDE values
are in `results/all_8b_guide_n120/`.

7. Adaptive injection:
   ```
   python src/run_adaptive_injection.py --seeds 7,11,13,17,19
   ```

`bypass_pct` in `results/all/adaptive_injection.json` is a legacy name. It is
the gate-release rate: the fraction of summaries written from the adaptive
templates that the gate marks `EMIT`. The run does not count how many of those summaries
actually contain the planted false claim, so the field is not an estimate of
released-and-unsupported outputs over outputs that contain the claim.

`E3_false_block_pct` is also a legacy name. It is the share of control
summaries routed to review. It is not a human-labeled false-positive rate.

8. Rebuild tables and figures:
   ```
   python src/make_tables.py --json results/all/consolidated.json --out results/all/tables
   python figures/make_figs.py
   ```

`figures/make_figs.py` reads AIT-ADS from `results/all/` and GUIDE from
`results/all_n120/`. The y-axis label is "Checked-field pass rate (%)".

Committed aggregates can be checked without re-running the models. A rerun
draws new LLM text, so C2 and the judge counts will be close, not identical.
Validation time and summary time were measured on the machine below.

## Environment used for the reported runs

- Python 3.9.6
- `pydantic-ai-slim` 0.8.1 (the 1.x line needs Python >= 3.10; this pin does not)
- Ollama 0.30.11
- `llama3.2:3b` id `a80c4f17acd5`
- `llama3.1:8b` id `46e0c10c039e`
- macOS 15.7.4, Apple M4 Max (14 cores), 36 GB RAM

Sampled GUIDE runs use `GUIDE_Train.csv` only. File names, row counts, and
SHA-256 checksums of the copies used for these runs are in
`data/DOWNLOAD_DATASETS.md`.

## Human-labeled study

The blinded sheet with four annotators' labels and adjudicated outcomes is at
`results/labels/label_sheet_filled_with_notes.csv`. Reproduce every reported
number with:

```
python src/score_labels.py
```

That command uses `results/labels/label_sheet_filled_with_notes.csv` and
`results/labels/label_key.csv`.

This prints Fleiss' kappa over the four annotators and the gate-vs-adjudicated
confusion cells (75 / 75 / 143 / 7 on all 300 pairs). The 300 pairs are
balanced by corpus and gate decision. They are not a sample of how often the
gate fires in an operational queue.

## License

See `LICENSE`.
