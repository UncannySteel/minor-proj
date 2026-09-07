# Issue Report Classification - Prototype Results

Dataset: **NLBSE'23 Tool Competition** issue report classification ([source](https://github.com/nlbse2023/issue-report-classification)). Labels are real GitHub labels applied by project maintainers.

All models are fitted on the training file and scored on the competition's **official held-out test file**, which is never seen during training or model selection.

> The NLBSE'23 ranking metric is micro-averaged F1. For single-label multi-class classification that is arithmetically identical to accuracy, so the accuracy column below is directly comparable to published competition results.

| model | accuracy | precision (macro) | recall (macro) | **Macro-F1** | MCC | note |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| majority class | 0.5359 | 0.1340 | 0.2500 | **0.1745** | 0.0000 | always predicts `bug` |
| TF-IDF + LogisticRegression | 0.8082 | 0.6554 | 0.7451 | **0.6877** | 0.6847 | text only, fitted in 10s |
| TF-IDF + LinearSVC | 0.8224 | 0.6864 | 0.6899 | **0.6881** | 0.6932 | text only, fitted in 10s |
| metadata-only LogisticRegression | 0.5132 | 0.4533 | 0.5347 | **0.4152** | 0.3442 | 25 structural features, no text at all |
| text only (distilbert) | 0.8367 | 0.7010 | 0.7710 | **0.7271** | 0.7273 | val Macro-F1 0.7206 |
| metadata only (MLP) | 0.6205 | 0.4571 | 0.5189 | **0.4568** | 0.4228 | val Macro-F1 0.4543 |
| LATE FUSION: distilbert + metadata | 0.8283 | 0.6918 | 0.7646 | **0.7203** | 0.7172 | val Macro-F1 0.7173 |

## Per-class F1

Where the macro average actually comes from. `question` and `documentation` are the minority classes and are where models differ most.

| model | bug | feature | question | documentation |
| --- | ---: | ---: | ---: | ---: |
| text only (distilbert) | 0.8910 | 0.8491 | 0.5528 | 0.6153 |
| metadata only (MLP) | 0.7008 | 0.6632 | 0.3524 | 0.1109 |
| LATE FUSION: distilbert + metadata | 0.8773 | 0.8467 | 0.5506 | 0.6066 |

## Published NLBSE'23 baselines, for context

Reported by the competition organisers on **this exact test file**, in micro-averaged F1 (= accuracy):

| system | accuracy / micro-F1 |
| --- | ---: |
| FastText (competition baseline) | 0.8510 |
| RoBERTa (competition baseline) | 0.8906 |
| **text only (distilbert)** (this prototype) | **0.8367** |

**This is not a like-for-like comparison and should not be presented as one.** Both published baselines were trained on the full ~1.2M-row training set; this prototype samples a fraction of it and trains for two epochs with no hyperparameter search. RoBERTa is also a substantially larger model than DistilBERT. The numbers are here as orientation - they say whether the pipeline is in the right neighbourhood, not whether it wins.

## Does metadata fusion help?

This is the question the prototype was built to answer, and the answer is whatever the numbers say.

| variant | Macro-F1 | accuracy |
| --- | ---: | ---: |
| text only (distilbert) | 0.7271 | 0.8367 |
| LATE FUSION: distilbert + metadata | 0.7203 | 0.8283 |

Difference in Macro-F1: **-0.0068** - **fusion hurt**.

### Per-class, text-only vs fusion

| class | text only | late fusion | delta |
| --- | ---: | ---: | ---: |
| bug | 0.8910 | 0.8773 | -0.0137 |
| feature | 0.8491 | 0.8467 | -0.0024 |
| question | 0.5528 | 0.5506 | -0.0023 |
| documentation | 0.6153 | 0.6066 | -0.0087 |

Fusion gains on: nothing. Fusion loses on: `bug`, `feature`, `question`, `documentation`.

A null result here is still a result, and it is the honest reading of these numbers. The structural features are deliberately shape-and-provenance signals rather than vocabulary - body length, stack traces, checklists, whether the reporter is the repo owner. The metadata branch on its own scores well above the majority baseline, so that signal is genuinely there. It simply stops being *new* information once a fine-tuned transformer has read the prose.

Two mechanisms are worth separating before concluding metadata is useless, and neither is tested here: the fused vector is 768 text dimensions against 32 metadata dimensions, so the fusion layer can learn to ignore the smaller branch almost for free; and the text encoder is fine-tuned end-to-end while the metadata branch trains from scratch alongside it. Widening the metadata branch, gating the two modalities explicitly, or freezing the text encoder so metadata has to carry weight would each give it a fairer test.

