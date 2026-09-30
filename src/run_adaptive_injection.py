"""Adaptive-injection run.

Non-adaptive E3 strings change fields the validator checks, so the gate withholds
them. This run keeps those fields correct and adds text the validator does not
extract (product, finding title, hostname, domain, file path, port, remediation
with no checked entity). It prints the fraction of those strings the gate emits.
Deterministic; no LLM.

Usage: python3 run_adaptive_injection.py --seeds 7,11,13,17,19 --n 40
"""
from __future__ import annotations
import argparse, collections
import nlip_soc as core
import generators as gen
import run_experiment as R

CORPORA = [("synthetic", "synthetic", None), ("ait_csv_pooled", "ait_ads", "csv_pooled"),
           ("guide_train", "guide", None)]


def run_one(label, dataset, mode, n, seed):
    scenario = "russellmitchell"
    items, adapters, _ = R.load_dataset(dataset, None, n, seed, scenario, mode or "auto")
    per = collections.Counter(); per_tot = collections.Counter()
    naive_caught = naive_tot = 0
    for it in items:
        ev = adapters[it["detector"]](it["native"])
        # adaptive: should bypass (EMIT)
        for adv in gen.ADAPTIVE_INJECTIONS:
            s = gen.injection_adaptive(ev, adv)
            emitted = core.validate_faithfulness(s, ev).decision == "EMIT"
            per[adv["type"]] += int(emitted); per_tot[adv["type"]] += 1
        # non-adaptive control: should be caught (for contrast)
        inj = gen.INJECTIONS[0]
        na = gen.injection_naive(ev, inj)
        naive_caught += int(core.validate_faithfulness(na, ev).decision != "EMIT"); naive_tot += 1
    return per, per_tot, naive_caught, naive_tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="7,11,13,17,19")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--only", default=None, help="comma-separated labels to run")
    a = ap.parse_args()
    seeds = [int(s) for s in a.seeds.split(",")]
    only = set(a.only.split(",")) if a.only else None

    print(f"Adaptive injection (bypass = gate EMITs the injected summary). seeds={seeds}\n")
    for label, dataset, mode in CORPORA:
        if only and label not in only:
            continue
        agg = collections.Counter(); agg_tot = collections.Counter(); nc = nt = 0
        for sd in seeds:
            per, per_tot, naive_c, naive_t = run_one(label, dataset, mode, a.n, sd)
            agg.update(per); agg_tot.update(per_tot); nc += naive_c; nt += naive_t
        total_emit = sum(agg.values()); total = sum(agg_tot.values())
        print(f"## {label}  (n={a.n}/seed x {len(seeds)} seeds)")
        for t in sorted(agg_tot):
            print(f"   {t:22s} bypass {100*agg[t]/agg_tot[t]:5.1f}%  ({agg[t]}/{agg_tot[t]})")
        print(f"   {'OVERALL adaptive bypass':22s}       {100*total_emit/total:5.1f}%  ({total_emit}/{total})")
        print(f"   {'non-adaptive caught':22s}       {100*nc/nt:5.1f}%  ({nc}/{nt})\n")


if __name__ == "__main__":
    main()
