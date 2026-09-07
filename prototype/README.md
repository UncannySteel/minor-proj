# Issue Report Classification — working prototype

A minimal, end-to-end implementation of the late-fusion architecture from `../idea/`: a transformer
text encoder and a metadata encoder are fused *late*, feeding a shared representation and a
classifier head. No UI, no API, no database — the point is to show that the model pipeline runs, is
measured against a published benchmark, and to answer one concrete question honestly.

**The question:** does fusing structural metadata with a transformer text encoder beat the text
encoder alone at classifying GitHub issues?

One command, download to results:

```bash
python -m src.run_all
```

---

## Dataset

[**NLBSE'23 Tool Competition — issue report classification**](https://github.com/nlbse2023/issue-report-classification)

| | |
| --- | --- |
| train | ~1.2M labelled issues (sampled to 150k for the prototype) |
| test | 142,320 labelled issues — the competition's official held-out file |
| labels | `bug`, `feature`, `question`, `documentation` |
| columns | `id`, `labels`, `title`, `body`, `author_association` |

**The labels are real GitHub labels applied by project maintainers.** Nothing here is inferred,
derived, or keyword-matched. The train/test split is the competition's own, so the accuracy column
is comparable to published results rather than to a split invented for this repo.

Both files download automatically on first run — no Kaggle account, no API key.

> **Why not the Kaggle `davidshinn/github-issues` dataset?** It was the original plan, but it has
> only three columns — `issue_url`, `issue_title`, `body` — with no labels, no state, no priority
> and no timestamps. It was built for seq2seq title generation. Training on it would have required
> manufacturing targets with keyword rules, which measures how well a model recovers a regex rather
> than how well it classifies issues. NLBSE'23 gives real supervision and a citable benchmark for
> the same task, and it is the dataset the literature review in `../idea/` already identifies as
> the standard one.

---

## The experiment

Three model variants, identical training code, same architecture class — only the branches change:

| variant | text branch | metadata branch |
| --- | :---: | :---: |
| text only | DistilBERT | — |
| metadata only | — | MLP |
| **late fusion** | DistilBERT | MLP |

Running only the fusion model would produce a number with nothing to compare it against, so all
three run by default and land in the same table. `results/metrics.md` ends with a section that
states the verdict in whichever direction it goes.

**A null or negative result is still a result.** The structural features are deliberately
shape-and-provenance signals rather than vocabulary, so if the transformer already recovers them
from the prose, fusion has nothing left to add — and that is worth knowing before building anything
on top of it.

---

## What it found

150k train, the full 142k official test set, DistilBERT, 2 epochs. Live numbers are always in
`results/metrics.md`.

| model | accuracy | **Macro-F1** | MCC |
| --- | ---: | ---: | ---: |
| majority class | 0.5359 | **0.1745** | 0.0000 |
| metadata-only LogisticRegression | 0.5132 | **0.4152** | 0.3442 |
| metadata only (MLP) | 0.6205 | **0.4568** | 0.4228 |
| TF-IDF + LogisticRegression | 0.8082 | **0.6877** | 0.6847 |
| TF-IDF + LinearSVC | 0.8224 | **0.6881** | 0.6932 |
| text only (DistilBERT) | 0.8367 | **0.7271** | 0.7273 |
| late fusion (DistilBERT + metadata) | 0.8283 | **0.7203** | 0.7172 |

**Four things to take from this.**

**1. Accuracy alone would have lied to you.** The `majority class` row scores 0.5359 accuracy - it
sounds like a working model, and it never predicts anything but `bug`. Its Macro-F1 is 0.1745.
Every metric decision in this repo follows from that one row.

**2. The transformer earns its place.** DistilBERT beats the best TF-IDF baseline by roughly +0.039
Macro-F1 (0.7271 vs 0.6881). That gap is large, holds across runs, and is what justifies the extra
complexity - measured rather than assumed.

**3. The fusion effect is below the noise floor. This is the important finding.** Two full runs of
this pipeline, *same seed, same data, same code*, produced:

| run | text only | late fusion | delta |
| --- | ---: | ---: | ---: |
| 1 | 0.7217 | 0.7239 | **+0.0022** |
| 2 | 0.7271 | 0.7203 | **-0.0068** |

**Opposite signs.** Seeding fixes initialisation, shuffling and dropout, but CUDA training is not
deterministic - cuDNN selects kernels adaptively and the backward pass accumulates with atomics.
The run-to-run swing is around +/-0.007 Macro-F1, which is *larger than the effect being measured*.

So the honest answer from a single run is **"not measurable"**, not a direction. Run with
`--seeds 3` (or more) to get a mean and an error bar; `results/metrics.md` reports it that way, and
explicitly refuses to give a direction when N=1.

This generalises beyond this repo: a paper reporting a single-run fusion delta on a setup like this
would be reporting whichever way the dice fell. Worth knowing before building on the result.

Two confounds are also worth naming before concluding metadata is useless, and neither is tested
here: the fused vector is 768 text dimensions against 32 metadata dimensions, so the fusion layer
can learn to ignore the smaller branch almost for free; and the text encoder is fine-tuned
end-to-end while the metadata branch trains from scratch beside it. Note the metadata branch alone
reaches 0.4568 Macro-F1 against a 0.1745 floor - the signal is genuinely there. It just stops being
*new* information once a transformer has read the prose.

**4. The benchmark has a train/test leak.** 1,510 of 150,000 sampled training rows (1.0%) have
normalised text identical to a row in the official test file. That is a property of the published
dataset, not of our sampling, so the same rate should be expected across the full 1.2M training
set. Any result reported on this benchmark without that check is partly measuring memorisation.
Every number above is computed after the overlap was removed.


### The model

```
title + body ──► DistilBERT ─────────────────────► 768 ─┐
                                                         ├─► concat ─► dropout ─► Linear(256) ─► ReLU ─► classifier (4)
metadata ──────► Dense(64) ─► ReLU ─► Dense(32) ──► 32 ──┘
(25 floats)
```

Class-weighted cross-entropy, inverse frequency. That is not decoration: `bug` and `feature` are
roughly 90% of the label mass, and an unweighted loss is happiest ignoring `question` and
`documentation` entirely — which scores well on accuracy and collapses on Macro-F1. Early stopping
watches validation Macro-F1, never accuracy, for the same reason.

### Metadata features (25)

All available the moment the issue is opened — nothing depends on comments, assignment, or anything
else that happens after creation.

- **body (14)** — length, line count, mean word length, uppercase ratio, and binary flags for code
  block, stack trace, reproduction checklist, embedded image, markdown headings, issue-template
  boilerplate, version string, URLs, question marks
- **title (5)** — length in characters and words, question mark, uppercase ratio, and whether the
  reporter self-tagged (`[BUG]`, `(feature)`)
- **author (6)** — one-hot over `author_association`. Whether the reporter is the repository OWNER
  or a drive-by NONE is real provenance and is not recoverable from prose.

---

## Pipeline

| stage | file | what it does |
| --- | --- | --- |
| 1. download + ingest | `src/ingest.py` | fetches both archives, streams the CSVs in 100k-row chunks, samples across the whole file |
| 2. cleaning | `src/clean.py` | 9 filters per split, each logged; normalisation, dedup, bot and non-English removal, train/test overlap check |
| 3. metadata features | `src/features.py` | 25 structural features from title, body and author association |
| 4. split | `src/splits.py` | the competition's official protocol; a validation slice carved from train for early stopping only |
| 5. baselines | `src/baselines.py` | majority, TF-IDF+LR, TF-IDF+SVM, metadata-only LR |
| 6. model | `src/model.py`, `src/train.py` | DistilBERT + metadata MLP, late fusion |
| 7. evaluation | `src/evaluate.py` | metrics table, confusion matrices, one-vs-rest ROC and PR |

Sampling reads a random fraction of *every* chunk rather than taking the head, because the CSV is
ordered and a head-sample would skew both the label mix and the projects represented.

The train/test overlap check is worth calling out: any training row whose normalised text also
appears in the official test file is dropped. An overlap would inflate every number reported here,
and finding none is itself a result worth stating.

---

## Metrics

Accuracy is reported alongside macro precision / recall / F1 and MCC. On this label set accuracy
alone is misleading — the `majority class` row makes the point in a single line, scoring over 50%
accuracy against a Macro-F1 near 0.17.

> **Comparability note.** The NLBSE'23 competition ranks entries on micro-averaged F1. For
> single-label multi-class classification, micro-F1 is arithmetically identical to accuracy, so the
> accuracy column is directly comparable to published competition numbers. It is not reported twice
> under two names.

### Published baselines on this exact test file

The competition organisers report:

| system | accuracy / micro-F1 |
| --- | ---: |
| FastText | 0.8510 |
| RoBERTa | 0.8906 |

`results/metrics.md` reproduces these next to the prototype's own best row. **It is not a
like-for-like comparison and should not be presented as one** — both were trained on the full
~1.2M-row training set, while this prototype samples 150k and trains for two epochs with no
hyperparameter search, and RoBERTa is a substantially larger model than DistilBERT. They are there
to say whether the pipeline is in the right neighbourhood, not whether it wins.

---

## Running it

```bash
pip install -r requirements.txt
python -m src.run_all
```

150k sampled training rows, the full 142k official test set, DistilBERT, 2 epochs. Roughly 25–30
minutes on an RTX 4070 SUPER, most of it the two transformer variants. The archives (~570 MB total)
download once into `data/raw/` and the cleaned data is cached to parquet, so `--skip-ingest` makes
subsequent runs go straight to modelling.

### Smoke test

```bash
python -m src.run_all --quick
```

Full pipeline on 12k train / 5k test with the from-scratch BiGRU encoder, in under a minute. Real
data and real labels — the numbers are genuine, just weaker than a full run.

### Flags

| flag | effect |
| --- | --- |
| `--quick` | 12k train / 5k test, BiGRU encoder, 1 epoch. Writes to `results/quick/` so it cannot overwrite a full run |
| `--encoder gru` | from-scratch BiGRU instead of DistilBERT — **zero downloads**, insurance against a failed `pip install` or HuggingFace outage |
| `--skip-ingest` | reuse the cleaned parquet files |
| `--train-rows N` | change the training sample size |
| `--epochs N` | override the epoch count |
| `--skip-baselines` | skip the sklearn rungs and go straight to the neural variants |
| `--clean-only` | stop after ingest and cleaning; regenerates `data_quality.md` without touching the GPU |
| `--seeds N` | repeat each neural variant over N seeds and report mean ± sd. **Use this for any fusion claim** — at N=1 the effect is inside the noise |

---

## Outputs

| file | contents |
| --- | --- |
| `results/data_quality.md` | row counts at every cleaning step for both splits, label distribution, author-association breakdown, example rows, feature statistics |
| `results/metrics.md` | paste-ready results table, per-class F1, and the fusion verdict |
| `results/metrics.csv` | the same numbers, machine readable |
| `results/confusion_*.png` | one per model |
| `results/roc_*.png` | one-vs-rest ROC, one curve per class |
| `results/pr_*.png` | one-vs-rest precision-recall |

---

## What this prototype does not do

Stated plainly, because a guide will ask.

- **Single task.** The dataset carries one label column, so there is one head. A second task would
  have to be manufactured, which is exactly what moving to this dataset was meant to avoid.
- **No cross-repository split.** NLBSE'23 does not ship a repository column, so grouping by project
  is not possible. The official held-out split is used instead — and the train/test label shares
  match to within 0.4%, which indicates it is a *random* split rather than a temporal or
  per-project one. That makes this an in-distribution held-out test, a weaker generalisation claim
  than unseen-project evaluation would be. Worth naming rather than glossing over.
- **No temporal split.** No timestamps in the released columns.
- **No resolution-time or lifecycle prediction.** Needs `created_at` / `closed_at`, which this
  release does not carry.
- **A sample, not the full corpus.** 150k of ~1.2M training rows by default, for runtime. Raise it
  with `--train-rows`.
- **No hyperparameter search.** One configuration, two epochs.

## Next iteration, in order

1. **Train on the full 1.2M rows** and more epochs — the cheapest available improvement, and the
   fairest comparison to competition entries.
2. **Repository metadata via the GitHub API**, keyed on the `id` column. That unlocks the
   cross-repository split, and with `created_at` / `closed_at` also unlocks lifecycle and
   resolution-time prediction — which would restore the multi-task framing on real labels.
3. **Stronger encoders** — RoBERTa, or a domain-pretrained model, against the same protocol.
4. **Calibration and explainability** — confidence calibration and per-prediction attribution.
5. **Only then**, the FastAPI + dashboard layer from `../idea/implementation-draft.md`.

---

## Ten-minute walkthrough

1. **`results/data_quality.md`, attrition table.** Every filter, with row counts, for both splits.
   The cleaning is auditable line by line.
2. **The Observations block, straight after it.** Two findings about the benchmark itself: the
   1,510-row train/test leak, and the evidence that the official split is random rather than
   temporal. Leading with what you found *in the data* rather than what your model scored sets a
   different tone for the rest of the conversation.
3. **Label distribution.** Real imbalance: `bug` and `feature` are ~90%, `documentation` 4.3%.
   This sets up every metric decision that follows.
4. **`results/metrics.md`, the `majority class` row.** 0.5359 accuracy, 0.1745 Macro-F1. The
   argument for the metric choice, in one row.
5. **The TF-IDF rows, then DistilBERT.** 0.6881 → 0.7271 Macro-F1. That ~+0.039 is what justifies
   the transformer; without the baseline it would be an unsupported claim.
6. **The `metadata-only` rows.** No text at all, and 0.4568 Macro-F1 against a 0.1745 floor.
   Structure and provenance carry real signal on their own.
7. **The fusion verdict — the part worth spending time on.** Running the identical pipeline twice
   gave fusion deltas of `+0.0022` and `−0.0068`: opposite signs, same seed. The effect is smaller
   than CUDA run-to-run noise, so a single run cannot answer the question, and `metrics.md` refuses
   to give a direction when N=1. This is the most transferable thing in the repo — it is a claim
   about experimental method, not about this dataset.
8. **A confusion matrix** — `confusion_late-fusion-distilbert-metadata.png`. 84/87/70/67% on the
   diagonal, and the off-diagonal shows `question` losing 17% to `bug`, which is a sensible
   mistake rather than a broken model.
9. **Then the limitations**, particularly the missing repository column and what the GitHub API
   would unlock next.
