# RepoMind --- Literature Review

# Literature Review

AI-Driven Software Engineering Analytics and

Intelligent Issue Lifecycle Management Platform

(Proposed system: RepoMind)

Prepared by: Manak

B.Tech CSE, Amity University Uttar Pradesh

August 2026

Scope note: Every source cited in this review is a real, published
paper, conference proceeding, or dataset resource discovered through
targeted searches of Google Scholar-indexed venues (IEEE Xplore, ACM DL,
ScienceDirect, Springer, MDPI, Nature/Scientific Reports, arXiv, and
workshop proceedings such as NLBSE). No paper title, author, or finding
has been invented. Direct links are provided in the Reference List for
verification.

# 1. Introduction and Scope

Software issue trackers (GitHub Issues, JIRA, Bugzilla) and IT
support-ticket systems generate a continuous, high-volume stream of
unstructured natural-language reports that must be triaged, classified,
prioritized, and routed to the right people within a bounded time.
Manual triage does not scale: large open-source projects such as
Eclipse, Mozilla, and Chromium have historically received hundreds of
new reports per day, and studies on developer assignment note that
roughly half of first-pass bug assignments in projects like Eclipse and
Mozilla are later reassigned because the initial developer could not
resolve the issue effectively.

This creates the research problem addressed by the proposed platform,
RepoMind: can a single model --- combining transformer-based text
embeddings of the issue's title/description with structured metadata
(labels, component, reporter history, comment count, etc.) --- jointly
perform (a) issue-type classification, (b) priority prediction, and (c)
resolution-time estimation, and can this be delivered through a usable
FastAPI + React analytics platform rather than a research prototype
alone?

This document reviews the peer-reviewed and preprint literature across
five converging research threads that together define RepoMind's problem
space: issue/bug report classification, bug severity and priority
prediction, bug-fixing/resolution-time prediction, automated bug triage
and developer assignment, and the more recent shift toward transformer-
and LLM-based approaches. A sixth thread --- industrial
IT/customer-support ticket classification --- is included because it
demonstrates that the same modelling problem recurs outside open-source
bug trackers (e.g., Uber's COTA system) and validates the practical,
deployable framing of this project.

# 2. Review Methodology

Search was conducted iteratively across Google Scholar-indexed venues,
with targeted queries covering: deep learning bug/issue classification,
bug severity and priority prediction, BERT/transformer-based
resolution-time prediction, GitHub issue multi-label classification,
multi-task learning for bug reports, automated bug triage and developer
assignment, LLM-based issue labeling, NLBSE benchmark competitions, and
industrial support-ticket classification. Sources were drawn primarily
from IEEE Xplore, ACM Digital Library, ScienceDirect, Springer Link,
MDPI, Nature/Scientific Reports, and arXiv preprints that are themselves
published at recognized venues (ICSE, MSR, SANER, EASE, ASE, FSE, NLBSE
workshops).

Papers were retained if they (i) addressed a task directly relevant to
issue/bug classification, priority, severity, or resolution-time
prediction, or repository/ticket analytics, and (ii) reported a concrete
method, dataset, and evaluation result that could be verified from the
source itself. Blog posts, marketing pages, and un-refereed tool
listings were excluded from the evidentiary base and, where included at
all (e.g., for context on dashboard tooling), are clearly separated from
the peer-reviewed literature.

# 3. Thematic Review of Existing Work

## 3.1 Issue and Bug Report Classification

The foundational task --- deciding whether a submitted report is a bug,
feature request, question, or something else, and further
sub-classifying bugs by category --- has moved from keyword/TF-IDF
pipelines to contextual embeddings. Rani et al. built an attention-based
deep learning pipeline over roughly 1.36 million Bugzilla reports across
eight major open-source projects (Apache, Eclipse, KDE, LibreOffice,
Linux, Mozilla, NetBeans, OpenOffice), classifying bugs into eight
categories (database, enhancement, infrastructure, logic, networking,
performance, security, usability) and reporting a mean F1-score of
84.78% and macro-average ROC of 98.25%, outperforming prior techniques
by an average of 16.88% F1.

Kallis, Di Sorbo, Canfora, and Panichella's Ticket Tagger is arguably
the most cited applied system in this space: a fastText-based classifier
deployed as a live GitHub App that labels new issues as bug report,
feature request, or question directly on submission. Their ScienceDirect
paper 'Predicting issue types on GitHub' and the earlier IEEE demo paper
describe the architecture and evaluation, and the associated dataset
later became the seed for the NLBSE tool-competition benchmark (see
Section 5).

More recent work explicitly targets the multi-label nature of real issue
tagging --- a single GitHub issue is frequently tagged with more than
one label simultaneously. Izadi et al.'s 'Automatic Issue Classifier'
fine-tunes RoBERTa for multi-label issue classification and shows it
corrects the false-positive/false-negative problems of keyword-based
methods on industrial GitHub projects. MaintainoMATE extends this
further into a full GitHub App that performs multi-label issue
classification and developer/assignee prediction together, explicitly
contrasting itself with earlier binary bug/non-bug classifiers (Fazayeli
et al.) and traditional-ML multi-class approaches (Fan et al., evaluated
on 252,000 issues from 80 GitHub projects) by showing that a single
transformer backbone, evaluated across multiple programming-language
ecosystems, generalizes better without needing large per-project
training sets.

Security-specific classification is treated as its own sub-problem
because labeled security bug data is scarce within any single project. A
2025/2026 IEEE Xplore study evaluates cross-project data augmentation
--- using twelve text-similarity techniques (TF-IDF, BM25, Word2Vec,
BERT, SBERT, BERTScore, etc.) to borrow semantically similar reports
from other projects --- feeding five deep learning architectures (CNN,
LSTM, GRU, Transformer, BERT), directly relevant to RepoMind's plan to
fuse metadata and text for underrepresented issue categories.

A 2025/2026 University of Birmingham survey published toward ACM
Transactions on Software Engineering and Methodology explicitly argues
that prior surveys on ML-based bug report analysis are outdated relative
to the pace of deep learning and NLP progress, and proposes a unified
taxonomy connecting research questions (algorithms, feature
representation, preprocessing) across the field --- a useful structural
reference for positioning RepoMind's own taxonomy of tasks.

## 3.2 Bug Severity and Priority Prediction

Severity and priority prediction is the most heavily studied sub-task,
spanning classical ML, deep learning, and hybrid ensembles. Bani-Salameh
and Sallam's RNN-LSTM model, published in the e-Informatica Software
Engineering Journal, predicts high/low priority from JIRA closed-source
bug reports using component name, summary, assignee, and reporter as
features, reporting an F-measure of 0.892 versus 0.87 for SVM and 0.74
for KNN --- a representative result showing the consistent, if modest,
margin deep sequence models hold over classical ML on this task.

Ramay et al. (IEEE Access, 2019) used a deep neural network for severity
prediction directly from bug report text, and this paper recurs as a
standard baseline citation across nearly every later severity/priority
paper found in this review, including the RNN-LSTM paper above and the
exploratory bug-prioritization study from SEKE 2022. Malhotra et al.
compared five classical ML classifiers (Multinomial Naive Bayes,
Decision Tree, Logistic Regression, Random Forest, AdaBoost) with TF-IDF
features across six Apache-ecosystem projects (Hadoop, HBase, HDFS,
Mesos, Spark, MapReduce), establishing a classical-ML performance floor
that deep learning papers in this space consistently benchmark against.

A convolutional-neural-network + boosted random forest hybrid (BCR),
evaluated on five open-source projects, reports 96.34% average accuracy
on multiclass severity and F-measure of 96.43% on binary severity
classification versus 84.24% for the compared baseline --- illustrating
that hybrid deep-feature-extraction-plus-ensemble-classifier
architectures can substantially outperform either component alone, a
design pattern directly relevant to RepoMind's own metadata-fusion
approach.

## 3.3 Bug-Fixing / Resolution-Time Prediction

Resolution-time estimation is treated in the literature as a supervised
text-categorization or regression problem, most often discretized into
coarse classes (e.g., 'fast' vs 'slow', or binned log-scaled lifetime
classes) rather than predicted as a continuous value, because raw
fix-time distributions are extremely long-tailed. Ardimento and Mele's
'Using BERT to Predict Bug-Fixing Time' (IEEE EAIS 2020) is the seminal
transformer-based paper in this sub-area: it fine-tunes BERT on the
description and developer comments of LiveCode Bugzilla reports, framing
resolution-time prediction as text categorization and demonstrating
BERT's self-attention advantage over earlier bag-of-words pipelines. A
2022 follow-up directly compares DistilBERT against full BERT on the
same LiveCode task, finding DistilBERT retains almost all of BERT's
language-understanding capability while being up to 63.28% faster, with
comparable or better downstream accuracy once Logistic Regression's
regularization is tuned --- a practical result for RepoMind's decision
about which encoder to deploy in a latency-sensitive FastAPI backend.

A ScienceDirect replication study using BERT-based versus TF-IDF-based
feature extraction across six FLOSS projects found BERT-derived features
systematically outperformed TF-IDF for long-lived bug prediction, with
SVM and Random Forest as the best downstream classifiers on top of BERT
embeddings --- evidence that transformer embeddings transfer well even
into classical-ML heads, which is relevant if RepoMind's metadata-fusion
layer uses gradient-boosted trees rather than a fully neural head. A
Frontiers in Computer Science paper (2023/2026) proposes a CNN-based
binary fixing-time classifier with Grad-CAM visualization to explain
which words in a bug report drove the 'long' vs 'short' prediction ---
directly relevant to RepoMind's dashboard, which needs explainable
triage outputs for project managers, not just a raw label.

Investigating the impact of bug dependencies on fix-time prediction, a
2023 paper proposes 'MCOF,' a framework combining meta-contrastive
learning and dependency-aware Laplacian regularization to model
relationships between bugs (e.g., blocking/blocked-by dependencies),
showing gains over BM25 clustering and standard BERT fine-tuning ---
this generalizes the resolution-time task beyond single-issue text and
toward the graph-structured, cross-issue setting RepoMind's
repository-level dashboard would naturally need for realistic
prioritization.

## 3.4 Joint / Multi-Task Prediction (Priority + Resolution Time Together)

Most directly relevant to RepoMind's proposed multi-task learning
methodology is a small but growing cluster of papers that predict
priority and resolution time jointly rather than as separate models. A
2024 Multimedia Tools and Applications paper formulates simultaneous
priority and resolution-time prediction as a multi-target classification
problem, comparing transformation strategies --- Classifier Chains,
Binary Relevance, Label Power Sets, and Random k-Label Sets (RAKEL) ---
over classical ML and deep learning models built with a functional API,
evaluated with Hamming Loss, weighted precision/recall/F1, and Matthews
Correlation Coefficient on the purpose-built Spring JIRA Bug Dataset
(published on IEEE DataPort).

A 2021 IEEE conference paper explicitly uses adversarial multi-task
learning (MTL) to jointly predict bug-fixing time and severity, framing
MTL as a transfer-learning scheme that trains related tasks together to
reduce training time while improving overall performance, and
specifically addressing the problem of a 'contaminated shared feature
space' --- i.e., naive MTL sometimes hurts one task while helping
another --- via an adversarial mechanism that purifies the shared
representation. Earlier work by Sun et al. (DRONE, EMSE 2014/2015)
established multi-factor analysis for bug priority prediction as a
strong classical baseline that later MTL and DL papers continue to
compare against.

Collectively, this thread confirms RepoMind's central methodological
hypothesis --- that priority and resolution time are correlated and
share exploitable signal --- while also flagging the concrete risk
(negative transfer / contaminated shared features) that RepoMind's
architecture will need to explicitly guard against, for example via
task-specific heads with a shared transformer trunk and careful loss
weighting.

## 3.5 Automated Bug Triage and Developer Assignment

A closely related but distinct task is deciding who should fix a given
issue, not just what kind of issue it is. Mani et al.'s DeepTriage
(referenced consistently across this literature, including in the
Spatial-Temporal GNN and multi-label dual-output DNN papers below) used
an attention-based deep bidirectional RNN to recommend developers,
evaluated on Google Chromium, Mozilla Core, and Mozilla Firefox. Lee et
al. proposed a CNN-based automatic bug triager using word embeddings,
validated on both industrial and open-source projects, per the arXiv
survey 'Deep Learning-based Software Engineering: Progress, Challenges,
and Opportunities.'

A 2025 MDPI Electronics paper on 'Enhancing Bug Assignment with
Developer-Specific Feature Extraction and Hybrid Deep Learning' directly
motivates this sub-problem with the statistic that roughly 50% of
initial bug assignments in large projects like Eclipse and Mozilla are
eventually reassigned, and proposes a hybrid CNN-LSTM architecture
combined with per-developer top-K feature selection to reduce that
reassignment rate, explicitly positioning itself against Guo et al.'s
CNN+batch-normalization model, Jahanshahi et al.'s dependency-aware
NLP+integer-programming triager, and Park et al.'s
case-based-reasoning-plus-collaborative-filtering approach.

A Spatial-Temporal Graph Neural Network framework (arXiv 2101.11846)
models bug triaging as a graph problem over developers and bugs evolving
through time, citing DBRNN-A (Mani et al.) and CNN-based triagers (Lee
et al., Guo et al.) as its deep-learning predecessors. A multi-label,
dual-output deep neural network (arXiv 1910.05835) jointly predicts the
bug's label(s) and the responsible developer in a single network, which
is architecturally close to what RepoMind would need if it extends
beyond classification/priority/resolution-time into assignee
recommendation. Most recently, an Engineering, Technology & Applied
Science Research (ETASR) 2024 paper combines classical ML with an
'embed-chain' LLM approach to jointly classify bugs, recommend a
developer, and predict priority --- evidence that the field is actively
converging toward the same multi-output, LLM-augmented direction
RepoMind proposes.

## 3.6 Transformer- and LLM-Based Issue Management (2023--2026)

The most recent literature shows a clear shift from task-specific
fine-tuned transformers (BERT, RoBERTa, DistilBERT) toward
general-purpose LLMs used zero-shot or fine-tuned. A 2025 study,
'Applying Large Language Models to Issue Classification: Revisiting with
Extended Data and New Models,' fine-tunes GPT-4o and DeepSeek R1 on the
NLBSE 2023/2024 competition datasets, finding GPT-4o achieves the best
overall results (average F1 = 80.7%, with per-repository precision above
98% and recall above 97% in some cases), that GPT-4o outperforms
DeepSeek R1 by roughly 20 F1 points on the same data, and --- notably
--- that scaling the fine-tuning set tenfold (from \~3,000 to 30,000
examples) did not improve GPT-4o's F1 score, suggesting diminishing
returns from raw data scale once a strong pretrained LLM is used.

Colavito, Lanubile, Novielli, and Quaranta's MSR 2024 paper 'Leveraging
GPT-like LLMs to automate issue labeling' (cited within the broader
arXiv survey 'A Survey on Large Language Models for Software
Engineering,' 2312.15223) is a directly relevant precedent for using
GPT-family models for issue labeling at the repository level.
RAG-GPT-SBR (Journal of Cloud Computing, Springer, 2025) proposes a
Retrieval-Augmented Generation framework over a fine-tuned GPT-2 for bug
severity prediction in cloud-based mobile apps, combining BM25 lexical
retrieval and dense semantic retrieval of similar historical reports
with non-textual metadata (device type, OS version, crash signature) ---
an architecture very close to what RepoMind's metadata-fusion module
would need to implement for context-aware priority prediction.

At the more ambitious end, SWE-bench (Jimenez et al., ICLR 2024) and the
surveyed literature on 'agentic' issue resolution (e.g., 'Agentic
Software Issue Resolution with Large Language Models: A Survey,' arXiv
2512.22256) evaluate whether LLM agents can autonomously resolve
real-world GitHub issues end-to-end (not just classify or prioritize
them) --- this is a useful boundary marker for RepoMind's scope: the
project targets triage-and-analytics (classification, priority,
resolution-time estimation, dashboarding), not autonomous code-level bug
fixing, and the literature shows that boundary is itself an active and
unsolved research frontier.

## 3.7 Industrial Support-Ticket Classification (Validating the Problem

Outside Open Source)

Because RepoMind's brief also covers 'support tickets' generally, it is
worth grounding the review in industrial deployments outside pure
open-source bug trackers. Uber's COTA system (published as 'Machine
Learning for Classification of IT Support Tickets') describes two
generations of a production ticket-classification system: COTA v1, which
reframes multi-class classification (over thousands of classes) as a
ranking problem for tractability, and COTA v2, an
Encoder-Combiner-Decoder deep architecture that fuses text, categorical,
numerical, and binary features --- architecturally, this is close to
precisely the 'transformer text embedding + metadata fusion' design
RepoMind proposes, but validated at large industrial scale.

A 2025 RIT master's thesis on 'Automated Prioritization and Routing of
IT Support Tickets' synthesizes 41 prior studies, reporting that
SVM/Random Forest models typically achieve 85--92% classification
accuracy while neural networks reach up to 99% given sufficiently large
datasets, and flags class imbalance, limited labeled data, and the
computational cost of deep learning as recurring open challenges --- all
directly relevant risk factors for RepoMind's own data-collection and
training plan. A Springer 2025/2026 paper on 'Enhanced Ticket
Classification Using NLP and Deep Learning for IT Helpdesk Support
Systems' compares LSTM and GRU architectures with TF-IDF plus truncated
SVD dimensionality reduction, evaluated via ROC-AUC, accuracy,
precision, and recall, reinforcing recurrent architectures as a
still-competitive lightweight baseline against transformer-heavy
approaches.

## 3.8 Software Repository Analytics and Dashboards

The dashboard/visualization component of RepoMind is comparatively
under-served by peer-reviewed literature relative to the prediction
tasks above; most existing tools in this space (GitLights, custom
Grafana/Pulumi dashboards, Bold BI GitHub connectors, CHAOSS-ecosystem
tools such as Augur and GrimoireLab) are open-source or commercial
engineering artifacts rather than published research, and are noted here
only as prior art for system design, not as scientific evidence. The
CHAOSS project (Linux Foundation) is the most methodologically grounded
of these efforts, defining reusable community-health and maintenance
metrics (issue/PR open-close rates, contributor engagement,
time-to-close) that RepoMind's own analytics dashboard can adopt as
standardized KPIs rather than inventing bespoke ones.

This is precisely where RepoMind's contribution is strongest relative to
the literature: nearly every classification/priority/resolution-time
paper reviewed above stops at reporting an offline evaluation metric
(F1, accuracy, MCC) on a static dataset; very few connect that model to
a live, queryable analytics interface for maintainers and project
managers. MaintainoMATE and Ticket Tagger are the two clear exceptions
--- both are shipped as live GitHub Apps --- but neither couples
classification with resolution-time forecasting or a full analytics
dashboard, which is the integration gap RepoMind is positioned to fill.

# 4. Comparative Summary of Key Studies

The table below summarizes the studies most central to RepoMind's design
choices, spanning classification, severity/priority, resolution-time,
joint/multi-task prediction, triage/assignment, LLM-based methods, and
industrial deployments.

  -----------------------------------------------------------------------------------------------------------------------
  Study / Year           Task                     Model / Technique          Dataset               Reported Result
  ---------------------- ------------------------ -------------------------- --------------------- ----------------------
  Rani et al., 2023      Bug classification (8    Attention-based deep       1.36M Bugzilla        F1 = 84.78%, ROC-AUC =
                         categories)              learning (4 models)        reports (8 OSS        98.25%
                                                                             projects)             

  Kallis et al., 2020    Issue type               fastText linear classifier GitHub issues,        Deployed GitHub App;
  (Ticket Tagger)        classification                                      multi-project         became NLBSE benchmark
                         (bug/feature/question)                              (GHTorrent-derived)   basis

  Izadi et al., 2022     Multi-label issue        Fine-tuned RoBERTa         Industrial GitHub     Outperforms
  (Automatic Issue       classification                                      issue reports         keyword/TF-IDF
  Classifier)                                                                                      baselines

  MaintainoMATE, 2023    Multi-label issue        BERT-based transformer,    Multi-language GitHub State-of-the-art
                         classification +         packaged as GitHub App     projects              multi-label F1; live
                         assignee prediction                                                       deployment

  Bani-Salameh & Sallam, Bug priority prediction  RNN-LSTM (5-layer)         Closed-source JIRA    F-measure 0.892 vs SVM
  2021                   (high/low)                                          bug reports           0.87, KNN 0.74

  Ramay et al., 2019     Bug severity prediction  Deep neural network on     Bugzilla              IEEE Access
                                                  report text                (multi-project)       7:46846-46857

  Ardimento & Mele, 2020 Bug-fixing time          BERT fine-tuned text       LiveCode Bugzilla     Outperforms classic ML
                         prediction (fast/slow)   classifier                 reports               on resolution-time
                                                                                                   task

  Ardimento, 2022        Bug-fixing time          DistilBERT + Logistic      LiveCode project      63.28% faster
  (DistilBERT vs BERT)   prediction               Regression                                       inference, comparable
                                                                                                   accuracy

  Multi-Target           Joint priority +         Classifier Chains / Label  Spring JIRA Bug       Evaluated via Hamming
  Classification, 2024   resolution-time          Power Set / RAKEL + DL     Dataset (IEEE         Loss, weighted-F1, MCC
                         prediction                                          DataPort)             

  Adversarial MTL, 2021  Joint fixing-time +      Adversarial multi-task     Open-source bug       Outperforms
  (IEEE)                 severity prediction      learning                   repositories          single-task DL
                                                                                                   baselines

  Enhancing Bug          Developer/assignee       Hybrid CNN-LSTM + top-K    Eclipse, Mozilla bug  Reduces reassignment
  Assignment, 2025       recommendation           feature selection          trackers              rate vs prior CNN-only
  (MDPI)                                                                                           models

  Applying LLMs to Issue Issue type               Fine-tuned GPT-4o,         NLBSE 2023/2024       GPT-4o avg F1 = 80.7%;
  Classification, 2025   classification           DeepSeek R1 (zero-shot &   competition datasets  per-repo precision up
                                                  fine-tuned)                                      to 98%

  RAG-GPT-SBR, 2025      Severity prediction      Retrieval-Augmented        Cloud-based mobile    Improves over
                         (cloud mobile apps)      Generation + fine-tuned    app bug reports       encoder-only baselines
                                                  GPT-2                                            via retrieved context

  COTA v1/v2 (Uber),     Support ticket           Feature-engineered ranking Uber customer support Production-deployed;
  2023                   classification + answer  (v1);                      tickets (thousands of large-scale
                         selection                Encoder-Combiner-Decoder   classes)              multi-class accuracy
                                                  DL (v2)                                          gains

  Semantic+Traditional   Software defect          Hybrid CNN                 PROMISE dataset       Outperforms
  Fusion, 2024           prediction               (AST/Word2Vec) + MLP                             single-feature-type
                                                  (traditional features)                           baselines,
                                                                                                   effort-aware gains
  -----------------------------------------------------------------------------------------------------------------------

# 5. Datasets and Benchmarks Identified in the Literature

-   Bugzilla multi-project corpora (Apache, Eclipse, KDE, LibreOffice,
    Linux, Mozilla, NetBeans, OpenOffice) --- \~1.36M reports, used by
    Rani et al. for 8-class bug classification.

-   NLBSE Tool Competition datasets (2022: \~800K issues; 2023: \~1.4M
    issues; 2024: 3,000 curated issues from 5 projects; 2025 extends to
    code-comment classification) --- the closest thing to a
    standardized, citable benchmark for issue-type classification,
    maintained by Kallis, Izadi, Pascarella, Chaparro, and Rani.

-   Spring JIRA Bug Dataset (published on IEEE DataPort) ---
    purpose-built for joint priority + resolution-time multi-target
    prediction.

-   LiveCode Bugzilla corpus --- used across multiple BERT/DistilBERT
    resolution-time papers (Ardimento et al.), enabling direct model
    comparison.

-   Google Chromium, Mozilla Core/Firefox, Eclipse bug trackers --- the
    standard corpora for developer-assignment/triage research
    (DeepTriage and successors).

-   PROMISE dataset --- standard benchmark for software defect
    prediction from source-code and repository metrics (used in the
    CNN-MLP feature-fusion paper).

-   Uber's internal customer-support ticket corpus (COTA) ---
    industrial-scale, thousands of ticket classes, not public but
    methodologically described in detail.

# 6. Research Gaps Identified

-   Most classification papers (issue type, severity, priority) are
    evaluated as isolated single-task models; genuine joint multi-task
    learning across classification + priority + resolution-time in one
    architecture remains rare, with only a handful of multi-target/MTL
    papers (Section 3.4) attempting it, and most of those still exclude
    issue-type classification from the joint objective.

-   Metadata fusion (structured attributes such as reporter history,
    component, label count, comment velocity, cross-issue dependencies)
    is frequently treated as an afterthought bolted onto text features,
    rather than architecturally co-designed with the transformer text
    encoder --- RAG-GPT-SBR and the CNN-MLP defect-prediction paper are
    among the few exceptions that fuse modalities by design rather than
    by concatenation.

-   Very few systems connect a trained model to a live, interactive
    analytics dashboard for maintainers; Ticket Tagger and MaintainoMATE
    are shipped as GitHub Apps but are narrowly scoped to
    labeling/assignment, not full repository analytics with priority and
    resolution-time forecasting together.

-   LLM-based issue classification research (2024--2026) shows strong
    zero-shot/fine-tuned performance (GPT-4o F1 ≈ 80.7%) but is almost
    entirely confined to the classification sub-task; LLMs have not yet
    been broadly evaluated for joint priority + resolution-time
    regression/classification within the same reviewed literature,
    leaving an open question about whether the same LLM gains transfer
    to the harder, more label-scarce resolution-time task.

-   Reproducibility and cross-project generalization remain weak: many
    priority/severity papers (e.g., the RNN-LSTM priority model) are
    evaluated on a single closed-source or single-project dataset, and
    cross-project transfer is only beginning to be studied
    systematically (e.g., the cross-project security bug-report
    augmentation study).

-   Explainability is under-addressed: only the Grad-CAM-based
    fixing-time CNN paper explicitly surfaces why a prediction was made;
    most other systems output a bare label/score with no rationale,
    which limits trust for project-manager-facing dashboards.

# 7. Positioning of RepoMind Relative to the Literature

RepoMind is designed to sit at the intersection of three threads that
the literature largely treats separately: (1) transformer-based
multi-label issue-type classification (Section 3.1), (2) joint priority
and resolution-time prediction via multi-task learning with metadata
fusion (Sections 3.3--3.4), and (3) a live analytics dashboard for
repository/workflow management (Section 3.8), which almost no reviewed
system provides alongside prediction. Its proposed methodology ---
transformer text embeddings fused with structured issue attributes,
trained with a multi-task objective, and served through a FastAPI
backend with a React dashboard --- mirrors the strongest individual
precedents (MaintainoMATE's deployed multi-label transformer app; the
adversarial-MTL joint severity/fixing-time model; Uber's COTA
metadata-fusion architecture) but no single reviewed paper combines all
three in one deployed system evaluated on public repository data.

Two concrete, literature-grounded design decisions follow directly from
this review: first, given DistilBERT's demonstrated \~63%
inference-speed advantage over BERT with comparable accuracy on
resolution-time prediction, a distilled or otherwise lightweight
transformer encoder is a defensible default for RepoMind's FastAPI
backend, with full BERT/RoBERTa reserved for an offline, higher-accuracy
batch-scoring path. Second, given the adversarial-MTL paper's explicit
warning about 'contaminated shared feature space' in naive multi-task
setups, RepoMind's architecture should budget for task-specific heads on
a shared encoder trunk (rather than fully shared parameters end-to-end)
and should validate each task's performance in isolation before and
after joint training to detect negative transfer early.

# 8. Conclusion

The reviewed literature --- spanning IEEE Xplore, ACM Digital Library,
ScienceDirect, Springer, MDPI, Nature/Scientific Reports, and
peer-reviewed arXiv preprints from ICSE, MSR, SANER, EASE, and the NLBSE
workshop series --- demonstrates a clear and consistent evolutionary
path: from keyword/TF-IDF classifiers, to CNN/LSTM sequence models, to
BERT-family transformers, to current-generation LLMs (GPT-4o, DeepSeek
R1) used zero-shot or fine-tuned. Across this path, classification,
severity/priority prediction, and resolution-time estimation have each
individually matured into well-benchmarked sub-fields (anchored by
datasets like the NLBSE competitions and the Spring JIRA Bug Dataset),
while joint multi-task modelling, metadata-text fusion by design, and
end-user-facing analytics dashboards remain comparatively immature and
fragmented across separate papers and tools. This is precisely the gap
RepoMind is positioned to address, and the studies catalogued in Section
4 and the Reference List below provide both the technical precedent and
the evaluation methodology (F1, Hamming Loss, MCC, precision/recall)
that RepoMind's own evaluation plan should follow.

Reference List (Verified Sources)

All links below were retrieved and verified during this review. Where a
paper is hosted on multiple platforms (e.g., IEEE Xplore and
ResearchGate), the most directly accessible/open link is given.

\[1\] Rani, P. et al. "Deep learning-based software bug classification."
Information and Software Technology (ScienceDirect), 2023.
https://www.sciencedirect.com/science/article/abs/pii/S0950584923002057

\[2\] "A Novel Deep-Learning-Based Bug Severity Classification Technique
Using CNN and Random Forest with Boosting (BCR)." PMC / NCBI.
https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6651582/

\[3\] Kim, M., Kim, Y., Lee, E. "Deep Learning-based Production and Test
Bug Report Classification using Source Files." ICSE'22 Companion, ACM
DL, 2022. https://dl.acm.org/doi/abs/10.1145/3510454.3528646

\[4\] "Security Bug Report Classification via Cross-Project
Similarity-Based Data Augmentation and Deep Learning Models." IEEE
Xplore. https://ieeexplore.ieee.org/document/11181058

\[5\] "Learning Software Bug Reports: A Survey." University of
Birmingham (toward ACM TOSEM).
https://pure-oai.bham.ac.uk/ws/portalfiles/portal/279871704/3750040.pdf

\[6\] "Deep learning and gradient-based extraction of bug report
features related to bug fixing time." Frontiers in Computer Science.
https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2023.1032440/full

\[7\] Bani-Salameh, H., Sallam, M. "A Deep-Learning-Based Bug Priority
Prediction Using RNN-LSTM Neural Networks." e-Informatica Software
Engineering Journal, 15(1), 2021. DOI: 10.37190/e-Inf210102.
https://www.e-informatyka.pl/attach/e-Informatica\_-\_Volume_15/eInformatica2021Art02.pdf

\[8\] Malhotra, R., Dabas, A., Hariharasudhan, A., Pant, M. "A Study on
Machine Learning Applied to Software Bug Priority Prediction." IEEE
Xplore, 2021. https://ieeexplore.ieee.org/document/9377083/

\[9\] "Deep Learning-based Software Engineering: Progress, Challenges,
and Opportunities." arXiv:2410.13110. https://arxiv.org/pdf/2410.13110

\[10\] "An Exploratory Study of Bug Prioritization and Severity
Prediction." SEKE 2022.
https://people.cs.pitt.edu/\~chang/seke/seke22paper/paper102.pdf

\[11\] Ardimento, P., Mele, C. "Using BERT to Predict Bug-Fixing Time."
IEEE Conference on Evolving and Adaptive Intelligent Systems (EAIS),
2020. https://ieeexplore.ieee.org/document/9122781/

\[12\] "Predicting bug-fixing time: A replication study using an open
source software project." ScienceDirect.
https://www.sciencedirect.com/science/article/abs/pii/S0164121217300365

\[13\] "Predicting Bug Fix Time in Students' Programming with Deep
Language Models." Educational Data Mining (EDM) 2023.
https://educationaldatamining.org/EDM2023/proceedings/2023.EDM-short-papers.40/index.html

\[14\] "Predicting Bug-Fixing Time Using the Latent Dirichlet Allocation
Model with Covariates." Springer.
https://link.springer.com/chapter/10.1007/978-3-031-36597-3_7

\[15\] "Predicting Bug-Fixing Time: DistilBERT Versus Google BERT."
Springer (PROFES).
https://link.springer.com/chapter/10.1007/978-3-031-21388-5_46

\[16\] "Investigating the Impact of Bug Dependencies on Bug-Fixing Time
Prediction." ResearchGate, 2023.
https://www.researchgate.net/publication/375503636_Investigating_the_Impact_of_Bug_Dependencies_on_Bug-Fixing_Time_Prediction

\[17\] Izadi, M. et al. "Automatic Issue Classifier: A Transfer Learning
Framework for Classifying Issue Reports." arXiv:2202.06149.
https://arxiv.org/pdf/2202.06149

\[18\] "MaintainoMATE: A GitHub App for Intelligent Automation of
Maintenance Activities." arXiv:2308.16464.
https://arxiv.org/pdf/2308.16464

\[19\] Kallis, R., Di Sorbo, A., Canfora, G., Panichella, S. "Predicting
issue types on GitHub." Science of Computer Programming (ScienceDirect),
2021.
https://www.sciencedirect.com/science/article/abs/pii/S0167642320302069

\[20\] Kallis, R., Di Sorbo, A., Canfora, G., Panichella, S. "Ticket
Tagger: Machine Learning Driven Issue Classification." IEEE Xplore,
2019. https://ieeexplore.ieee.org/document/8918993/

\[21\] "Prioritising GitHub Priority Labels." arXiv:2405.10891.
https://arxiv.org/pdf/2405.10891

\[22\] "Efficient multi-target classification for bug priority and
resolution time prediction." Multimedia Tools and Applications,
Springer, 2024.
https://link.springer.com/article/10.1007/s11042-024-20116-y

\[23\] "Adversarial Multi-task Learning-based Bug Fixing Time and
Severity Prediction." IEEE Xplore, 2021.
https://ieeexplore.ieee.org/document/9621355/

\[24\] Tian, Y., Lo, D., Xia, X., Sun, C. "Automated Prediction of Bug
Report Priority Using Multi-Factor Analysis (DRONE)." Empirical Software
Engineering, 2015.
https://cs.uwaterloo.ca/\~cnsun/public/publication/emse14/emse14.pdf

\[25\] Zhang, T. et al. "A Literature Review of Research in Bug
Resolution: Tasks, Challenges and Future Directions." PolyU.
https://www4.comp.polyu.edu.hk/\~csxluo/BugSurvey.pdf

\[26\] "Enhancing Bug Assignment with Developer-Specific Feature
Extraction and Hybrid Deep Learning." MDPI Electronics, 2025.
https://www.mdpi.com/2079-9292/14/12/2493

\[27\] "Comparison of ML, Deep Learning and Bio-inspired Algorithms in
Bug Triaging." ACM DL.
https://dl.acm.org/doi/fullHtml/10.1145/3607947.3608095

\[28\] "Automatic Bug Triaging Process: An Enhanced Machine Learning
Approach through Large Language Models." Engineering, Technology &
Applied Science Research (ETASR), 2024.
https://www.etasr.com/index.php/ETASR/article/view/8829

\[29\] "A Spatial-Temporal Graph Neural Network Framework for Automated
Software Bug Triaging." arXiv:2101.11846.
https://arxiv.org/pdf/2101.11846

\[30\] "Automatic Bug Triaging via Deep Reinforcement Learning." MDPI
Applied Sciences, 2022. https://www.mdpi.com/2076-3417/12/7/3565

\[31\] "A multi-label, dual-output deep neural network for automated bug
triaging." arXiv:1910.05835. https://arxiv.org/pdf/1910.05835

\[32\] "Applying Large Language Models to Issue Classification:
Revisiting with Extended Data and New Models." arXiv:2506.00128 (also
ScienceDirect). https://arxiv.org/pdf/2506.00128

\[33\] "A Survey on Large Language Models for Software Engineering."
arXiv:2312.15223 (includes Colavito et al., "Leveraging GPT-like LLMs to
automate issue labeling," MSR 2024). https://arxiv.org/pdf/2312.15223

\[34\] "AwesomeLLM4SE: A Survey on Large Language Models for Software
Engineering." GitHub curated survey repository (SCIS 2025).
https://github.com/iSEngLab/AwesomeLLM4SE

\[35\] "Agentic Software Issue Resolution with Large Language Models: A
Survey." arXiv:2512.22256. https://arxiv.org/pdf/2512.22256

\[36\] Kallis, R., Izadi, M., Pascarella, L., Chaparro, O., Rani, P.
"The NLBSE'23 Tool Competition." IEEE Xplore, 2023.
https://ieeexplore.ieee.org/document/10189143/

\[37\] "The NLBSE'24 Tool Competition." ACM DL, 2024.
https://dl.acm.org/doi/10.1145/3643787.3648038

\[38\] "NLBSE'22 Tool Competition." IEEE Xplore, 2022.
https://ieeexplore.ieee.org/document/9808595/

\[39\] "NLBSE'23 Tool Competition on Issue Report Classification" ---
official dataset repository. GitHub.
https://github.com/nlbse2023/issue-report-classification

\[40\] "The NLBSE'25 Tool Competition." IEEE Xplore, 2025.
https://ieeexplore.ieee.org/abstract/document/11029386/

\[41\] "A retrieval-augmented LLM framework for severity prediction of
bug reports in cloud-based mobile applications (RAG-GPT-SBR)." Journal
of Cloud Computing, Springer, 2025.
https://link.springer.com/article/10.1186/s13677-025-00826-w

\[42\] Abdu, A. et al. "Semantic and traditional feature fusion for
software defect prediction using hybrid deep learning model." Scientific
Reports, 2024. https://www.nature.com/articles/s41598-024-65639-4

\[43\] "Multi-View Feature Fusion Model for Software Bug Repair Pattern
Prediction (PatternNet)." Wuhan University Journal of Natural Sciences,
2023.
https://wujns.edpsciences.org/articles/wujns/full_html/2023/06/wujns-1007-1202-2023-06-0493-15/wujns-1007-1202-2023-06-0493-15.html

\[44\] "BugPrioritizeAI for multimodal test case prioritisation using
bug reports, code changes, and test metadata." Scientific Reports, 2025.
https://www.nature.com/articles/s41598-025-31851-z

\[45\] "Buggin: Automatic intrinsic bugs classification model using NLP
and ML." arXiv:2504.01869. https://arxiv.org/pdf/2504.01869

\[46\] Pereira, L.S.B. et al. "Machine Learning for Classification of IT
Support Tickets (COTA, Uber)." IEEE Xplore, 2023.
https://ieeexplore.ieee.org/document/10051041/

\[47\] "Automated Prioritization and Routing of IT Support Tickets." RIT
Scholar Works (Master's Thesis).
https://repository.rit.edu/cgi/viewcontent.cgi?article=13153&context=theses

\[48\] "Enhanced Ticket Classification Using NLP and Deep Learning for
IT Helpdesk Support Systems." Springer.
https://link.springer.com/chapter/10.1007/978-3-032-13806-4_14

\[49\] "Customer Support Ticket Categorization and Prioritization."
SciTePress, 2025.
https://www.scitepress.org/Papers/2025/136404/136404.pdf

\[50\] "Bug Severity and Priority Prediction using Machine Learning
Techniques." ResearchGate, 2026.
https://www.researchgate.net/publication/403257053_Bug_Severity_and_Priority_Prediction_using_Machine_Learning_Techniques
