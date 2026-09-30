"""Regenerate the paper figures from the committed results.

Reads results/all/consolidated.json (and results/all_n120 for GUIDE n=120)
and writes fig_e2.pdf and fig_runtime.pdf next to this script. No LLM, no network.

Usage: python figures/make_figs.py
"""
from __future__ import annotations
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
JSON = os.path.join(ROOT, "results", "all", "consolidated.json")

ORDER = ["ait_csv_pooled", "guide_train"]
NAMES = {"ait_csv_pooled": "AIT-ADS", "guide_train": "GUIDE"}


def load():
    d = json.load(open(JSON))
    agg = {a["label"]: a for a in d["aggregated"]}
    # GUIDE is reported at the larger n=120 sample
    n120 = os.path.join(ROOT, "results", "all_n120", "consolidated.json")
    if os.path.exists(n120):
        for a in json.load(open(n120))["aggregated"]:
            if a["label"] == "guide_train":
                agg["guide_train"] = a
    return agg


def mean(a, k):
    return a[k]["mean"]


def err(a, k):
    s = a[k]["std"]  # error bars are +/- 1 SD
    return [s, s]


def fig_e2(agg):
    conds = [("E2_C1_emitted_clean_pct", "C1: raw"),
             ("E2_C2_emitted_clean_pct", "C2: grounded"),
             ("E2_C3_emitted_clean_pct", "C3: grounded+gated")]
    colors = ["#c0562b", "#2e7d32", "#2f6db5"]
    x = np.arange(len(ORDER)); w = 0.26
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for i, (k, lab) in enumerate(conds):
        means = [mean(agg[c], k) for c in ORDER]
        errs = np.array([err(agg[c], k) for c in ORDER]).T
        ax.bar(x + (i - 1) * w, means, w, yerr=errs, capsize=3, label=lab,
               color=colors[i], edgecolor="black", linewidth=0.4)
    ax.set_xticks(x); ax.set_xticklabels([NAMES[c] for c in ORDER])
    ax.set_ylabel("Emitted-clean summaries (%)"); ax.set_ylim(0, 108)
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.13))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig_e2.pdf"))


def fig_runtime(agg):
    x = np.arange(len(ORDER))
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    sm = [mean(agg[c], "runtime_summarize_ms") for c in ORDER]
    vl = [mean(agg[c], "runtime_validate_ms") for c in ORDER]
    sme = np.array([err(agg[c], "runtime_summarize_ms") for c in ORDER]).T
    vle = np.array([err(agg[c], "runtime_validate_ms") for c in ORDER]).T
    ax.bar(x - 0.2, sm, 0.4, yerr=sme, capsize=3, label="LLM Summary",
           color="#5b6b80", edgecolor="black", linewidth=0.4)
    ax.bar(x + 0.2, vl, 0.4, yerr=vle, capsize=3, label="Deterministic validation",
           color="#2f6db5", edgecolor="black", linewidth=0.4)
    ax.set_yscale("log"); ax.set_ylabel("Time per alert (ms, log scale)"); ax.set_ylim(0.05, 3000)
    ax.set_xticks(x); ax.set_xticklabels([NAMES[c] for c in ORDER])
    for i in range(len(ORDER)):
        ax.text(i - 0.2, sm[i] * 1.18, f"{sm[i]:.0f}", ha="center", fontsize=8)
        ax.text(i + 0.2, vl[i] * 1.5, f"{vl[i]:.2f}", ha="center", fontsize=8)
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.15))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", linestyle=":", alpha=0.5, which="both")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig_runtime.pdf"))


if __name__ == "__main__":
    agg = load()
    fig_e2(agg)
    fig_runtime(agg)
    print("wrote fig_e2.pdf and fig_runtime.pdf in", HERE)
