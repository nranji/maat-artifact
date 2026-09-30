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
  all/                    3B AIT-ADS aggregates + adaptive injection
  all_n120/               3B GUIDE aggregates (n=120)
  all_8b/, all_8b_guide_n120/   8B aggregates
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

5. Run the five-seed E2/E3 sweep for the 3B model:
   ```
   export MAAT_OLLAMA_MODEL=llama3.2:3b
   python src/run_all.py --paper --seeds 7,11,13,17,19 --out all
   ```

6. Repeat for the 8B model:
   ```
   export MAAT_OLLAMA_MODEL=llama3.1:8b
   python src/run_all.py --paper --seeds 7,11,13,17,19 --out all_8b
   ```

7. Run the adaptive-injection experiment:
   ```
   python src/run_adaptive_injection.py --seeds 7,11,13,17,19
   ```

8. Rebuild the paper's tables and figures:
   ```
   python src/make_tables.py --json results/all/consolidated.json --out results/all/tables
   python figures/make_figs.py
   ```

Committed aggregates (E2/E3, model comparison, runtime, adaptive injection)
are in `results/`. The reported numbers can be checked without re-running the models.

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
confusion cells (75 / 75 / 143 / 7 on all 300 pairs).

## License

See `LICENSE`.
