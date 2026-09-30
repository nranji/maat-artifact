"""Score the faithfulness gate against human labels.

Reads results/labels/label_sheet_filled_with_notes.csv (y/n in human_faithful_1..4)
and results/labels/label_key.csv (id -> gate_decision), joined on id.

Two to four labelers:
  - Cohen's kappa for 2 raters, Fleiss' kappa for 3 or 4, plus raw agreement.
  - Per row, human_faithful_adjudicated wins if it is filled. Otherwise the
    majority of the filled labels is used. An even split is skipped.
  - The gate comes from the key. It is scored on all resolved rows and again
    on rows where every labeler agrees.

Prints leaked (EMIT and unfaithful), caught, over-blocked, clean-emit,
EMIT precision, and recall on unfaithful.

Usage:
  python src/score_labels.py
  python src/score_labels.py --sheet path/to/sheet.csv --key path/to/key.csv
"""
from __future__ import annotations

import argparse
import csv
import itertools
import os

from paths import RESULTS

YES = {"y", "yes", "faithful", "1", "true", "t"}
NO = {"n", "no", "unfaithful", "0", "false", "f"}
ANN = ("human_faithful_1", "human_faithful_2", "human_faithful_3", "human_faithful_4")


def parse(v):
    v = (v or "").strip().lower()
    if v in YES:
        return True
    if v in NO:
        return False
    return None


def cohen(pairs):
    n = len(pairs)
    if not n:
        return None, 0, None
    po = sum(1 for a, b in pairs if a == b) / n
    ay = sum(1 for a, _ in pairs if a) / n
    by = sum(1 for _, b in pairs if b) / n
    pe = ay * by + (1 - ay) * (1 - by)
    return ((po - pe) / (1 - pe) if pe < 1 else 1.0), n, po


def fleiss(items):
    """items: list of label-lists, each of the SAME length r (raters), binary bools."""
    items = [it for it in items if len(it) >= 2]
    if not items:
        return None, 0
    r = len(items[0])
    items = [it for it in items if len(it) == r]
    N = len(items)
    # category counts per item: [n_true, n_false]
    p_true = sum(sum(1 for x in it if x) for it in items) / (N * r)
    p = [p_true, 1 - p_true]
    Pe = sum(pj * pj for pj in p)
    Pbar = 0.0
    for it in items:
        nt = sum(1 for x in it if x); nf = r - nt
        Pbar += (nt * nt + nf * nf - r) / (r * (r - 1))
    Pbar /= N
    return ((Pbar - Pe) / (1 - Pe) if Pe < 1 else 1.0), N


def confusion(rows_gt_gate):
    leaked = caught = overblock = cleanemit = 0
    for faithful, emit in rows_gt_gate:
        if emit and faithful:
            cleanemit += 1
        elif emit and not faithful:
            leaked += 1
        elif not emit and not faithful:
            caught += 1
        else:
            overblock += 1
    emitted = cleanemit + leaked
    unfaithful = leaked + caught
    prec = 100.0 * cleanemit / emitted if emitted else 100.0
    rec = 100.0 * caught / unfaithful if unfaithful else 100.0
    return dict(n=len(rows_gt_gate), cleanemit=cleanemit, leaked=leaked, caught=caught,
                overblock=overblock, prec=prec, rec=rec, emitted=emitted, unfaithful=unfaithful)


def show(title, c):
    print(f"\n=== {title} (n={c['n']}) ===")
    print(f"  EMIT & faithful     (clean-emit)   : {c['cleanemit']}")
    print(f"  EMIT & unfaithful   (LEAKED)       : {c['leaked']}")
    print(f"  REVIEW & unfaithful (caught)       : {c['caught']}")
    print(f"  REVIEW & faithful   (over-blocked) : {c['overblock']}")
    print(f"  EMIT precision                     : {c['prec']:.1f}%  ({c['cleanemit']}/{c['emitted']})")
    print(f"  recall on unfaithful               : {c['rec']:.1f}%  ({c['caught']}/{c['unfaithful']})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=os.path.join(
        RESULTS, "labels", "label_sheet_filled_with_notes.csv"))
    ap.add_argument("--key", default=os.path.join(
        RESULTS, "labels", "label_key.csv"))
    a = ap.parse_args()
    if not os.path.exists(a.sheet):
        raise SystemExit(f"no label sheet at {a.sheet}; run make_label_sheet.py first")

    rows = list(csv.DictReader(open(a.sheet, encoding="utf-8")))
    key = {}
    if os.path.exists(a.key):
        for r in csv.DictReader(open(a.key, encoding="utf-8")):
            key[str(r["id"])] = (r.get("gate_decision") or "").strip().upper()

    # per-row annotator labels
    labelset = []
    for r in rows:
        labs = [parse(r.get(c)) for c in ANN]
        labs = [x for x in labs if x is not None]
        labelset.append(labs)
    n_raters = max((len(x) for x in labelset), default=0)

    # agreement
    print("=== inter-annotator agreement ===")
    if n_raters >= 3:
        k, N = fleiss([x for x in labelset if len(x) == n_raters])
        print(f"  {n_raters} labelers: Fleiss' kappa = {k:.3f}  (over {N} fully labeled rows)")
        ks = []
        for i, j in itertools.combinations(range(n_raters), 2):
            pr = [(parse(r.get(ANN[i])), parse(r.get(ANN[j]))) for r in rows]
            pr = [(x, y) for x, y in pr if x is not None and y is not None]
            kk, _, _ = cohen(pr)
            if kk is not None:
                ks.append(kk)
        if ks:
            print(f"  mean pairwise Cohen's kappa   = {sum(ks)/len(ks):.3f}")
    elif n_raters == 2:
        pr = [(parse(r.get(ANN[0])), parse(r.get(ANN[1]))) for r in rows]
        pr = [(x, y) for x, y in pr if x is not None and y is not None]
        k, N, po = cohen(pr)
        print(f"  two labelers: Cohen's kappa = {k:.3f}  raw agreement {po*100:.1f}%  (over {N} rows)")
    else:
        print("  (need at least two of human_faithful_1..4 filled)")

    # ground truth: adjudicated override, else majority vote
    full, unanimous = [], []
    scored = skipped = contested = no_key = 0
    for r, labs in zip(rows, labelset):
        adj = parse(r.get("human_faithful_adjudicated"))
        if adj is not None:
            faithful = adj
        elif labs:
            t = sum(1 for x in labs if x); f = len(labs) - t
            if t == f:
                contested += 1
                continue  # tie (2 disagreeing labelers) with no adjudication
            faithful = t > f
        else:
            skipped += 1
            continue
        gate = key.get(str(r.get("id")))
        if gate is None:
            no_key += 1
            continue
        emit = gate == "EMIT"
        scored += 1
        full.append((faithful, emit))
        if labs and all(x == labs[0] for x in labs) and len(labs) >= 2:
            unanimous.append((faithful, emit))

    if not full:
        raise SystemExit("\nno rows scored (fill human_faithful_* and provide the key)")
    print(f"\nrows scored: {scored}  (unlabeled: {skipped}; contested ties: {contested}; missing key: {no_key})")
    show("gate vs human, all resolved rows", confusion(full))
    if unanimous:
        show("gate vs human, unanimous subset", confusion(unanimous))


if __name__ == "__main__":
    main()
