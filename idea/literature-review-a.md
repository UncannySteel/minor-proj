# RepoMind --- Beta Literature Review

RepoMind AI-Driven Software Engineering Analytics and Intelligent Issue
Lifecycle Management

# Beta Literature Review

     Research landscape • Existing systems • Models • Datasets • Results • Gaps •
                            Proposed research direction

Prepared as a research foundation for the RepoMind review presentation.

Important: paper claims and links in this document are based on verified
research records and open-access/full-text sources where available.
Where a source did not expose a result in the accessible record, no
result is invented.

RepoMind --- Beta Literature Review 1

# 1. Executive Summary

RepoMind sits at the intersection of several established
software-engineering research problems: issue-type classification,
priority/severity prediction, resolution-time estimation,
developer/issue routing, lifecycle prediction, and repository analytics.
The literature shows substantial progress in each individual area, but
the research is fragmented across tasks, datasets, repositories, and
evaluation protocols.

The strongest research opportunity is therefore not simply "use BERT to
classify GitHub issues." Prior work has already demonstrated classical
NLP, CNNs, BERT/Transformer models, multi-task learning,
GitHub-integrated applications, and joint priority/time prediction.
RepoMind should instead be framed around leakage-aware,
cross-repository, multi-task issue lifecycle intelligence: use only
information available when an issue is created, fuse transformer text
representations with structured metadata, jointly model complementary
targets, and evaluate generalization across repositories and time.

Core research question: Can a creation-time, transformer-plus-metadata
multi-task model provide robust issue classification and lifecycle
predictions that generalize beyond the repositories used for training?

Key methodological principle: a high random-split accuracy is not
sufficient. Macro-F1, MCC, temporal evaluation, cross-repository
evaluation, calibration, explainability, and practical inference cost
should be considered alongside accuracy.

Source grounding: the uploaded project material emphasizes the same
issues---class imbalance, label leakage, cross-repository evaluation,
creation-time feature contracts, and a three-task minor-project scope.
■filecite■turn2file0■

RepoMind --- Beta Literature Review 2

# 2. Research Landscape

The field has evolved approximately as follows:

Rule/manual triage → TF-IDF + classical ML → CNN/RNN/LSTM →
BERT/Transformers → multi-task learning → text + metadata/code fusion →
LLM-assisted triage → end-to-end intelligent lifecycle systems.

This evolution matters because the novelty threshold has moved.
Classification itself is mature. Transformer classification is also
established. Multi-task triage exists. Priority plus resolution-time
prediction exists. RepoMind therefore needs a more precise contribution
than "an AI issue classifier."

The 2025 Journal of Systems and Software comparative study is especially
relevant: it notes that prior studies use different evaluation designs
and often emphasize accuracy, making results hard to compare. It
evaluates nine ML techniques on three datasets and explicitly considers
generalizability, explainability, and maintenance cost. Open-access
paper / ScienceDirect.

RepoMind --- Beta Literature Review 3

# 3. Core Research Papers

     The following studies form the backbone of the beta review. The table deliberately separates what each paper studied
     from what RepoMind should learn from it.

Pap Study / Venue Task Data / Model Result / lesson er

1 Antoniol et al. (2008) CASCON '08 Classical issue classification
77--82% correct decisions Is it a bug or an enhancement?: a text-based
Mozilla, Eclipse, JBoss approach to classify change requests Alternating
Decision Trees, Naive Paper / DOI Bayes, Logistic Regression

2 Fan et al. (2017) IEEE/ACM ESEM Large-scale GitHub issue Reported
study Where is the Road for Issue Reports classification emphasizes
classification Classification Based on Text Mining? 80 popular projects;
\>252k effectiveness and semantic Paper / DOI GitHub issue reports
characteristics Text-mining / two-stage classification

3 Kallis et al. (2021) Science of Computer GitHub issue labeling
Reasonably high Predicting Issue Types on GitHub / Ticket Programming
\~30,000 GitHub issues effectiveness; deployed as Tagger ML on issue
title + description; a GitHub-integrated tool Paper / DOI GitHub app

4 Ahmed et al. (2021) IEEE Access Category + priority \~88.8% category;
\~90.4% CaPBug: A Framework for Automatic Bug 2,000+ Mozilla/Eclipse bug
priority Categorization and Prioritization Using NLP reports and Machine
Learning Algorithms Naive Bayes, Random Forest, Paper / DOI Decision
Tree, Logistic Regression + SMOTE

5 Umer, Liu & Illahi (2020) IEEE Transactions on Priority prediction
Study reports effective CNN-Based Automatic Prioritization of Bug
Reliability Bug-report corpora multiclass prioritization Reports
CNN-based NLP Paper / DOI

6 Aung et al. (2022) Journal of Systems and Issue type + developer
assignment Outperformed comparison Multi-triage: A multi-task learning
framework Software 11 open-source projects approaches in experiments for
bug triage Multi-task model; text encoder + Paper / DOI AST encoder;
contextual augmentation

7 Ardimento & Mele (2020) IEEE EAIS Resolution-time prediction Effective
bug-fixing-time Using BERT to Predict Bug-Fixing Time Bug tracking data
prediction reported Paper / DOI BERT; text + developer comments

8 Noyori et al. (2023) Frontiers in Computer Fix-time prediction +
explainability \~75--80% accuracy for Deep Learning and Gradient-Based
Science \>36k bug reports short/long fixing-time Extraction of Bug
Report Features Related to CNN + Grad-CAM classification Bug Fixing Time
Paper / DOI

9 Madaraboina et al. (2024) Multimedia Tools and Priority + resolution
time Reports improvements Efficient multi-target classification for bug
Applications Spring JIRA bug reports across multi-target metrics
priority and resolution time prediction Classifier Chains, Binary Paper
/ DOI Relevance, Label Powerset, RAkEL + ML/DL

10 Arshad et al. (2024) AI Severity prediction Reported +1.7--10.7%
SevPredict: Exploring the Potential of Large Public bug datasets
accuracy vs prior SOTA; up Language Models in Software Maintenance GPT-2
vs BERT-based baselines to +41.3% MCC Paper / DOI

11 Laiq et al. (2025) Journal of Systems and Benchmark/evaluation
methodology Shows highest predictive A comparative analysis of ML
techniques for Software Three datasets accuracy is not always the bug
report classification Nine ML techniques incl. best practical choice
Paper / DOI BERT/RoBERTa/LLMs/AutoML

    RepoMind — Beta Literature Review                                                                                                               4

Pap Study / Venue Task Data / Model Result / lesson er

12 Wang et al. (2023) IEEE Transactions on
Methodological/reproducibility Highlights reproducibility, Machine/Deep
Learning for Software Software Engineering perspective replicability,
applicability Engineering: A Systematic Literature Review 1,428 ML/DL SE
papers, and generalizability Paper / DOI 2009--2020 concerns Systematic
literature review

RepoMind --- Beta Literature Review 5

# 4. What the Literature Establishes

## 4.1 Issue Classification

Antoniol et al. provide an early foundation: issue text can distinguish
bugs from other change requests, with 77--82% correct decisions across
Mozilla, Eclipse and JBoss. The key lesson is that issue classification
is established research territory, not a new problem. Verified DOI.

Kallis et al. move the problem to GitHub and into a usable product:
Ticket Tagger analyzes title and description and automatically assigns
issue labels. Their evaluation covered about 30,000 GitHub issues. Free
arXiv paper.

NLBSE 2023 further demonstrates the scale of modern issue classification
research, with a large issue-report classification benchmark and
transformer baselines. This supports using an established taxonomy
rather than inventing labels only for RepoMind.

## 4.2 Priority / Severity

CaPBug demonstrates that classical NLP + ML can jointly support
categorization and prioritization. The study used more than 2,000
Mozilla/Eclipse bug reports and reported approximately 88.8% category
accuracy and 90.4% priority accuracy after class balancing. The critical
methodological lesson is that class imbalance must be addressed and
reported explicitly. IEEE Access DOI.

SevPredict moves severity prediction into the LLM era with GPT-2. Its
reported gains include approximately 1.7--10.7 percentage points in
accuracy and up to 41.3% MCC improvement against comparison methods. The
paper reinforces that imbalanced classification should be assessed with
more than accuracy. Open-access paper.

## 4.3 Resolution-Time Prediction

Ardimento and Mele formulate bug-fixing-time prediction as supervised
text categorization and use BERT. An important RepoMind caution is
feature timing: their input includes developer comments, so a strict "at
issue creation" model must define what information is legally available
at inference time. IEEE DOI.

Madaraboina et al. are especially close to RepoMind because they
simultaneously predict priority and resolution time using multi-target
strategies. This means RepoMind should not claim that joint
priority/time prediction is unprecedented. Springer DOI.

## 4.4 Multi-Task Learning

Aung et al.'s Multi-triage model jointly predicts issue type and
developer assignment, using text and AST encoders and contextual
augmentation. It was evaluated across eleven open-source projects. This
is strong precedent for a shared representation with multiple task
heads. Open-access accepted version.

RepoMind --- Beta Literature Review 6

# 5. Research Gaps

Gap 1 --- Fragmented task coverage The literature commonly solves one or
two triage problems at a time: classification, priority, developer
assignment, duplicate detection, or fixing-time prediction. Multi-task
work exists, but a unified lifecycle-oriented framing remains less
common.

Gap 2 --- Bug-centric datasets A large part of the literature uses
Bugzilla/JIRA bug reports. GitHub issue ecosystems include bugs,
enhancements, questions, documentation and other issue types. RepoMind
should explicitly distinguish general issue intelligence from bug-only
prediction.

Gap 3 --- Cross-repository generalization Random splits can make a model
look strong while testing it on issues that resemble its training
distribution. A stronger experiment is to train on several repositories
and test on a repository the model has never seen.

Gap 4 --- Temporal / creation-time leakage Resolution time and priority
can be contaminated by information generated after issue creation:
comments, assignee changes, reactions, closure fields, milestones or
post-triage activity. RepoMind should define a creation-time feature
contract and prohibit post-creation information from the prediction
input.

Gap 5 --- Class imbalance Critical issues and minority categories are
often rare. Accuracy can therefore be misleading. RepoMind should
prioritize Macro-F1 and MCC, alongside per-class precision/recall and
confusion matrices.

Gap 6 --- Evaluation beyond accuracy The 2025 JSS comparative study
explicitly argues that predictive accuracy is only one dimension;
generalizability, explainability and maintenance cost matter too.
Open-access JSS article.

Gap 7 --- Research-to-workflow integration Ticket Tagger demonstrates
that model output can be integrated into GitHub. RepoMind should
therefore treat deployment and dashboard analytics as the application
layer, while keeping the research contribution centered on the model,
evaluation design and generalization.

RepoMind --- Beta Literature Review 7

# 6. Research-Driven RepoMind Architecture

The following architecture is a research-derived proposal rather than a
claim that it already exists in the literature.

GITHUB / ISSUE TRACKER

Title + Body + Creation-time Metadata

↓

Transformer Text Encoder Metadata Encoder

Semantic representation Structured representation

■■

Late Fusion / Shared Representation

↓

Task 1: Issue Category Task 2: Lifecycle Outcome Task 3: Resolution Time

↓

Confidence + Explanation + Repository Analytics

↓

FastAPI Backend → React Dashboard

Recommended baseline ladder: TF-IDF + Logistic Regression → TF-IDF + SVM
→ metadata-only model → BiGRU → transformer text-only → transformer +
metadata → multi-task transformer + metadata.

Recommended ablations: text-only vs metadata-only vs fusion; single-task
vs multi-task; random vs temporal vs cross-repository split.

RepoMind --- Beta Literature Review 8

# 7. Experimental Design

A publication-quality RepoMind evaluation should make the model compete
against meaningful baselines rather than only against a weak
implementation.

Dimension Recommended evaluation Why

Classification Macro-F1, weighted-F1, precision, recall, MCC, confusion
Protects against majority-class illusion matrix

Resolution time MAE if regression; Macro-F1 if bucketed; calibration
Measures practical forecasting quality

Generalization Random split + temporal split + unseen-repository split
Tests whether the model transfers

Ablation Text only / metadata only / fusion Shows where performance
comes from

MTL value Single-task vs shared multi-task model Tests whether tasks
actually help each other

Practicality Latency, memory, throughput, model size Accuracy is not the
whole deployment decision

Explainability Feature attribution / error analysis / confidence
Supports maintainer trust

The 2023 IEEE TSE systematic review of 1,428 ML/DL software-engineering
papers specifically highlights concerns around reproducibility and
replicability. RepoMind should therefore publish preprocessing rules,
splits, seeds, feature contracts, baselines and evaluation scripts where
possible. Free full-text PDF.

RepoMind --- Beta Literature Review 9

# 8. What to Say to the Mentor

30-second version "I studied the literature on automated software issue
triage and found that issue classification, priority prediction,
resolution-time prediction and multi-task triage are already established
research problems. Existing work ranges from classical NLP to CNNs,
BERT, GPT-2 and multi-task architectures. The gap I see is not another
classifier; it is a leakage-aware and cross-repository lifecycle model
that combines transformer text representations with creation-time
metadata and evaluates whether the learned representation actually
generalizes to unseen projects."

If asked what is already solved: GitHub issue labeling has been
demonstrated by Ticket Tagger; category and priority have been studied
by CaPBug; issue type + developer assignment by Multi-triage; BERT has
been used for fixing-time prediction; and priority + resolution time
have been jointly modeled by Madaraboina et al.

If asked what RepoMind adds: a unified research framing around
creation-time information, multi-task lifecycle prediction,
text/metadata fusion, cross-repository evaluation, rigorous
imbalance-aware metrics, and a practical analytics layer.

If asked why not just use GPT: because the research question is not
"which model sounds best?" We need controlled baselines, ablations,
reproducible evaluation, latency/cost analysis and evidence of
generalization. The 2025 comparative study supports evaluating beyond
accuracy.

RepoMind --- Beta Literature Review 10

# 9. Recommended Research Roadmap

Phase Work Output

Phase 1 Literature + dataset Freeze taxonomy, collect candidate
datasets, define inclusion/exclusion criteria, record provenance.

Phase 2 Leakage audit Define creation-time feature contract; remove
post-creation variables; document target construction.

Phase 3 Baselines TF-IDF/LR, TF-IDF/SVM, metadata-only, simple neural
baseline.

Phase 4 Transformer Fine-tune a compact transformer; establish text-only
performance.

Phase 5 Fusion Add structured creation-time metadata; compare early/late
fusion.

Phase 6 Multi-task Compare independent heads vs shared representation.

Phase 7 Generalization Run random, temporal and unseen-repository tests.

Phase 8 Analysis Ablation, minority-class analysis, calibration, error
taxonomy and explainability.

Phase 9 Deployment FastAPI inference service + React analytics
dashboard.

Phase 10 Paper Position contribution against the verified literature;
publish code/data protocol where licensing permits.

RepoMind --- Beta Literature Review 11

# 10. Verified Paper & Resource Links

The links below are intended as navigation to the actual research
records/full-text sources used for this beta review. Publisher records
may be paywalled; where an open-access or repository copy was verified,
that is linked separately. - Antoniol et al. (2008) --- ACM DOI - Kallis
et al. (2021) --- free arXiv version - Kallis et al. (2021) ---
ScienceDirect record - Aung et al. (2022) --- ScienceDirect - Aung et
al. --- UTS open-access repository - Aung et al. --- accepted manuscript
PDF - Ardimento & Mele (2020) --- IEEE DOI - Madaraboina et al. (2024)
--- Springer DOI - Arshad et al. (2024) --- open-access SevPredict -
Noyori et al. (2023) --- open-access - Laiq et al. (2025) ---
ScienceDirect - Laiq et al. (2025) --- free repository PDF - Wang et
al. (2023) --- free IEEE TSE PDF - NLBSE Issue Report Classification
resources

Note on evidence discipline This beta document preserves the distinction
between verified source findings and RepoMind design inference. A result
is not reported merely because it would be plausible. Before using this
as the final IEEE literature review, the next pass should expand the
matrix to roughly 30--50 papers and verify every dataset size, metric,
model variant and experimental split against the paper itself. End of
beta literature review.

RepoMind --- Beta Literature Review 12
