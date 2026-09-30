# Downloading the real datasets

MAAT runs E1/E2/E3 on two public datasets. Neither is redistributed in this
artifact (publisher terms). Download them onto your machine and place them
under `data/` as shown below. `.gitignore` already excludes those folders.

- **AIT-ADS** — Wazuh, Suricata, and AMiner alerts from multi-step attack
  scenarios (Landauer et al., CSET '24; Zenodo `10.5281/zenodo.8263181`,
  https://github.com/ait-aecid/alert-data-set).
- **GUIDE** — Microsoft SOC triage records with incident-grade labels
  (Freitas et al., arXiv:2407.09017), hosted on Kaggle as
  "Microsoft Security Incident Prediction".

## Expected layout (repository root)

```
data/
  ait_ads/
    alerts_csv.zip            # reduced labelled CSV (required for paper E2/E3)
    alerts_raw/               # optional; Zenodo JSON for raw mode
      russellmitchell_wazuh.json
      russellmitchell_aminer.json
      ...
  guide/
    GUIDE_Train.csv
    GUIDE_Test.csv            # used by run_dataset_checks.py (E1-full)
```

## AIT-ADS

1. Create `data/ait_ads/`.
2. From the AIT-ADS release (Zenodo record 8263181 or the GitHub repository),
   copy the reduced labelled archive to `data/ait_ads/alerts_csv.zip`.
   After unzipping it should contain per-scenario `*_alerts.txt` files
   (e.g. `russellmitchell_alerts.txt`) with columns
   `time,name,ip,host,short,time_label,event_label`.
3. Optional raw mode: download `ait_ads.zip` from
   https://zenodo.org/records/8263181, unzip into `data/ait_ads/alerts_raw/`,
   and confirm:
   ```
   ls data/ait_ads/alerts_raw/*.json
   ```

CSV mode is what the paper's sampled E2/E3 numbers use. Raw mode adds Wazuh
rule levels, the network 5-tuple, and full log lines.

## GUIDE

1. Create `data/guide/`.
2. Install the Kaggle CLI (`pip install kaggle`) with a `~/.kaggle/kaggle.json`
   token, search for "Microsoft Security Incident Prediction", then:
   ```
   kaggle datasets download -d <owner>/<slug> -p data/guide
   unzip data/guide/*.zip -d data/guide
   ```
3. Confirm:
   ```
   ls data/guide/*.csv
   ```
   You should have `GUIDE_Train.csv` and, for the full-corpus check,
   `GUIDE_Test.csv`.

## Running after download

From the repository root, with dependencies installed
(`pip install -r requirements.txt`):

```bash
# sampled AIT-ADS (CSV) and GUIDE
python src/run_experiment.py --dataset ait_ads --mode csv_pooled --n-per-detector 40
python src/run_experiment.py --dataset guide --n-per-detector 40

# AIT-ADS raw Zenodo alerts (optional)
python src/run_experiment.py --dataset ait_ads --mode raw --scenario russellmitchell --n-per-detector 40

# paper multi-seed sweep (requires Ollama; see README)
export MAAT_OLLAMA_MODEL=llama3.2:3b
python src/run_all.py --paper --seeds 7,11,13,17,19 --out all
```

Results are written under `results/<out>/`.

### Real LLM summaries

By default, if Ollama is not reachable, grounded summaries come from the
deterministic template. To use the local model used in the paper:

```bash
bash setup_ollama.sh
export MAAT_OLLAMA_MODEL=llama3.2:3b
python src/run_all.py --paper --seeds 7,11,13,17,19 --out all
```
