# Faithfulness labeling guide (MAAT human study)

Label whether each summary matches the structured event in that row. The sheet has the event fields and the summary. Generator source and the gate decision are in `label_key.csv`. Do not open that file until labeling is done.

## Who labels and how

Four annotators label **independently**, without discussing rows or seeing each other's answers:

- Annotator *i* fills `human_faithful_i` (`human_faithful_1` … `human_faithful_4`).
- Use `y` for faithful and `n` for not faithful.

Then run `python src/score_labels.py`. With four annotators it reports **Fleiss' kappa** over all four columns. The **majority vote** is used only when `human_faithful_adjudicated` is empty; even splits (2–2) are "contested" unless that adjudicated column is filled. Filling `human_faithful_adjudicated` always overrides the vote for that row. The released sheet already has an adjudicated label on every row. The scorer reports the gate's precision, recall, leaked, and over-blocked on all resolved rows and, separately, on the **unanimous** subset (rows where all four labelers agree).

## What "faithful" means

Compare the `summary` only against the event fields in that row: `product`, `title`, `severity`, `src_ip`, `dst_ip`, `user`. Do not use outside knowledge.

Mark **`y`** if every concrete claim in the summary is supported by those fields and the summary asserts no concrete value for a field shown as `UNKNOWN`. Omitting detail or awkward wording is still `y`; only added or contradicted facts make it `n`.

## Two kinds of violation: in-scope vs out-of-scope of the gate

The gate checks severity, IP addresses, CVEs, and user names. In the `notes` column, record which kind of problem you saw.

**In scope of the gate** (the gate is expected to catch these):
- a severity that contradicts the event, or a severity stated when the event severity is `UNKNOWN`;
- an IP address not in the event;
- a CVE identifier (these corpora carry none, so any CVE is unsupported);
- a user name introduced with the word "user"/"username" that is not in the event, or a user stated when the event user is `UNKNOWN`.

**Out of scope of the gate** (the current gate will NOT catch these; still mark the summary `n` and note it):
- a fabricated hostname, domain, or file path;
- a fabricated or wrong product name or finding title;
- a bare user name with no "user" token (e.g. "activity by mallory");
- a port number.

In the `notes` column, write whether the problem is in scope or out of scope. That split is what the paper reports.

## Misspellings and near-misses

Judge by field type. In a **descriptive text** field (product name, finding title), a spelling slip that still unambiguously refers to the same thing is faithful (`y`); note "typo". For example "AMiner" written as "anaminer" is `y`. Mark `n` when the misspelling names a different entity (e.g. "Suricata" when the event product is AMiner).

In an **identifier or value** field (IP address, port, CVE, user name, severity), any changed value is unfaithful (`n`), even by one character: "192.168.1.5" as "192.168.1.50" is a different host, "CVE-2023-1234" as "-1235" is a different vulnerability, "High" as "Low" is a different severity. If you are unsure whether a misspelling points to the same entity, mark `n` and note why.

## Judge only against the row's event fields

If the summary states something not represented in `product`, `title`, `severity`, `src_ip`, `dst_ip`, or `user`, and not derivable from the title text, treat it as unsupported.

## Report in the paper
Sheet size, that annotators were blind to the gate and to each other, Fleiss' kappa over four annotators, and the confusion counts against the adjudicated labels, with the in-scope vs out-of-scope split.
