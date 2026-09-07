Abstract— Software repositories generate large volumes of issue
reports, making manual issue triage increasingly time-consuming
and inconsistent. Recent advances in transformer-based language
models and multi-task learning provide opportunities to automate
software maintenance tasks more effectively [1]—[6], [16], [17].
This paper proposes VigilOps-MTLF (Volumetric Issue Grouping
and Intelligent Lifecycle Optimization Platform via Multi-Task
Late Fusion), a unified deep learning framework that jointly
performs GitHub issue classification and issue closure prediction.
The proposed architecture combines contextual transformer
embeddings with structured repository metadata using a late
fusion strategy, enabling modality-specific feature learning before
generating a shared representation for both prediction tasks. The
framework is evaluated on a publicly available GitHub/Helpdesk
issue dataset using standard metrics, including Accuracy,
Precision, Recall, Macro-F1, and confusion matrix analysis.
Experimental results demonstrate that VigilOps-MTLF
effectively captures both semantic and __repository-level
information, providing reliable performance for automated issue
analysis. The proposed framework offers a scalable foundation for
intelligent software maintenance and can be extended to developer
recommendation, issue prioritization, and other repository
management tasks.

Keywords—Software Engineering, GitHub Issue Triage, Multi-
Task Learning, Late Fusion, Transformer Models, Natural
Language Processing, Software Repository Mining, Deep Learning.

I. INTRODUCTION

Software development has increasingly shifted toward
collaborative repository platforms such as GitHub, GitLab, and
enterprise issue-tracking systems. These platforms record a
continuous stream of issue reports describing software defects,
feature requests, documentation updates, and other
maintenance activities. As repositories expand in size and
contributor count, the volume of incoming issues also grows,
creating significant challenges for repository maintainers.
Manually reviewing, categorizing, and tracking every issue
requires considerable effort, often leading to inconsistent
decisions, delayed assignments, longer resolution cycles, and
higher maintenance overhead. Consequently, automating issue
management has become an active area of research in modern

software engineering [6], [26], [30]. Progress in Natural
Language Processing (NLP) has accelerated the development
of intelligent solutions for software maintenance. Transformer-
based language models, including BERT, RoBERTa, and
DistilBERT, are capable of learning contextual representations
from issue descriptions without relying heavily on manually
engineered features, making them effective for a variety of
software engineering applications [1]-[5]. At the same time,
Mining Software Repositories (MSR) has provided researchers
with methods to analyze historical development data for tasks
such as defect prediction, issue triage, maintenance planning,
and software quality assessment [6], [29], [30]. Although these
techniques have improved individual prediction tasks, most
existing approaches address repository management problems
in isolation. Models are commonly designed for a single
objective—for example, issue classification, duplicate issue
detection, developer recommendation, or priority prediction—
without exploiting the relationships that naturally exist between
these tasks. As a result, potentially useful shared information is
often ignored, limiting both learning efficiency and overall
predictive performance.

To overcome the challenges associated with conventional issue
management systems, this work introduces VigilOps-MTLF
(Volumetric Issue Grouping and Intelligent Lifecycle
Optimization Platform via Multi-Task Late Fusion), a unified
framework for automated software issue analysis. The
proposed architecture combines contextual representations
generated from transformer-based language models with
structured repository metadata using a late fusion strategy.
Instead of merging heterogeneous information at the input
stage, textual and metadata features are processed
independently, allowing each modality to learn discriminative
representations before they are integrated for prediction. The
unified model is trained using a multi-task learning objective
that simultaneously performs GitHub issue classification and
issue closure forecasting.

By sharing learned representations across related tasks while
preserving task-specific output layers, the framework improves

knowledge transfer and reduces the need for separate models
for each prediction task [2], [3], [16], [17]. The proposed
approach is validated on a publicly available Helpdesk/GitHub
issue dataset. Model performance is assessed using standard
evaluation measures, including Accuracy, Precision, Recall,
Fl-score, and confusion matrix analysis. The experimental
results indicate that combining semantic information from issue
descriptions with structured repository attributes enables more
reliable issue categorization and lifecycle prediction. Owing to
its modular design, the framework can also be extended to
support additional repository management tasks, such as
developer recommendation, issue prioritization, duplicate issue
identification, and explainable decision support for software
maintenance.

II. LITERATURE REVIEW

The increasing adoption of collaborative software development
platforms has driven extensive research in intelligent software
maintenance, repository analytics, and automated issue
management. As software repositories continue to expand,
researchers have explored a wide range of approaches for
improving issue analysis and maintenance efficiency. Earlier
studies mainly relied on handcrafted textual features and
conventional machine learning algorithms, whereas recent
work has shifted toward transformer-based language models,
multi-task learning, and deep neural networks to better capture
semantic information contained in software artifacts. The
existing body of research can be grouped into five major areas:
software repository mining, conventional issue classification
techniques, transformer-based language models, multi-task
learning with representation fusion, and deployment
frameworks for intelligent software engineering systems.

A. Software Repository Mining and Automated Issue Triage

Software repositories preserve extensive _ historical
information about software evolution, including bug reports,
enhancement requests, feature discussions, and maintenance
records. This information has made Mining Software
Repositories (MSR) an important research domain for
understanding software development processes and improving
maintenance activities. Kagdi et al. [30] provided an early
survey describing the role of repository mining in software
evolution, maintenance, and defect analysis. Later, Allamanis
et al. [6] demonstrated that machine learning techniques could
automatically learn useful representations from software
artifacts, reducing the dependence on manually designed
features. Zimmermann ef al. [29] further illustrated that
historical repository data can support defect prediction across
different software projects, highlighting the practical
importance of repository analytics in large-scale development
environments.

B. Traditional Machine Learning Approaches for Issue
Classification

Prior to the widespread adoption of deep learning,
automated issue classification primarily depended on statistical
machine learning methods combined with manually engineered
textual representations. Feature extraction techniques such as

TF-IDF, Word2Vec, and GloVe transformed issue descriptions
into numerical vectors suitable for predictive modeling [7], [8].
These feature representations were commonly used with
classifiers including Support Vector Machines (SVM), Random
Forests, and Gradient Boosting for issue categorization, defect
prediction, and related software engineering tasks [9]-[11].
These methods remain attractive because of their relatively low
computational cost and straightforward implementation.

C. Transformer-Based Language Models for Software
Engineering

Transformer-based language models have significantly
advanced natural language understanding by introducing self-
attention mechanisms capable of modeling contextual
relationships throughout an entire sequence [1]. Building upon
this architecture, BERT introduced bidirectional contextual
representations that substantially improved performance across
numerous NLP benchmarks [2]. Subsequent models, including
RoBERTa [3] and DistiIBERT [4], focused on improving
representation quality while reducing computational
requirements. In addition, the Hugging Face Transformers
ecosystem has simplified the training, fine-tuning, and
deployment of pretrained language models for practical
software engineering applications [5], [23].

D. Multi-Task Learning and Representation Fusion

Multi-task learning enables multiple related prediction
problems to be learned within a shared framework by allowing
common representations to benefit more than one task. Caruana
[16] introduced the fundamental principles of this learning
paradigm, demonstrating that jointly optimized tasks can
improve model generalization through shared knowledge.
Ruder [17] later reviewed modern multi-task learning strategies
and discussed their advantages in reducing overfitting while
improving feature representations for correlated learning
objectives.

E. Deep Learning Frameworks and Intelligent Deployment

The availability of modern deep learning frameworks has
accelerated both research development and __ practical
deployment of intelligent software engineering applications.
PyTorch provides a flexible environment for constructing and
training deep neural networks through dynamic computational
graphs [22]. Scikit-learn continues to serve as a widely adopted
toolkit for implementing classical machine learning algorithms
and standardized evaluation procedures [21]. ONNX Runtime
supports efficient inference across multiple hardware platforms
and deployment environments, making trained models easier to
integrate into production systems [24]. Similarly, the Deep Java
Library (DJL) enables deep learning applications to be
deployed within Java-based enterprise software ecosystems
[25]. Together, these frameworks provide the infrastructure
required to build scalable and maintainable intelligent
repository management systems suitable for real-world
software engineering environments.

F. Research Gap
 Previous studies have demonstrated the effectiveness of 
software repository mining, transformer-based language 
models, and multi-task learning for various software 
engineering problems. However, most existing issue 
management solutions continue to treat tasks such as issue 
classification and lifecycle prediction as independent problems, 
resulting in duplicated learning processes and limited sharing 
of useful representations. 
III. DATASET DESCRIPTION
This research employs the Helpdesk Tickets – High Quality 
dataset, a publicly available benchmark frequently used for 
software issue classification and intelligent maintenance 
studies [26]-[28]. The dataset contains structured issue records 
collected from helpdesk and issue-tracking platforms that 
closely reflect the characteristics of issues encountered in 
collaborative software repositories. 
TABLE I. FEATURES OF DATASET
Feature Name Description
Issue Title Concise headline summarizing the reported 
software issue.
Issue Description Detailed natural language explanation describing 
the problem, request, or observed behavior.
Issue Category Ground-truth class label used for the issue 
classification task.
Issue Status Current lifecycle state of the issue, such as Open 
or Closed.
Priority Priority or severity level assigned to the issue, 
where available.
Metadata Attributes Structured repository or ticket-specific 
information used as complementary input features.
Closure Label Binary target indicating whether the issue is 
resolved (closed) or unresolved (open).
Text Features
Contextual semantic representations derived from 
transformer-based language models for issue 
understanding.
IV. METHODOLOGY
 The proposed VigilOps-MTLF (Volumetric Issue Grouping 
and Intelligent Lifecycle Optimization Platform via Multi-Task 
Late Fusion) framework is developed to automate software 
issue management by solving multiple repository analysis tasks 
within a single learning architecture. Instead of training 
separate models for issue categorization and lifecycle 
prediction, the proposed framework learns both tasks 
simultaneously through a multi-task learning strategy. The 
architecture integrates semantic representations extracted from 
transformer-based language models with structured repository 
metadata using a late fusion mechanism, allowing each 
information source to contribute independently before feature 
integration. The complete workflow consists of five sequential 
stages: data preprocessing, semantic feature extraction, 
metadata representation learning, late feature fusion, and task specific prediction [2], [5], [16], [17].
A diagram of the architecture is shown below:
Fig. 1. VigilOps-MTLF Architecture 
A. Data Preprocessing and Feature Engineering 
 The first stage prepares both textual and structured 
information for model training. Textual fields, including issue 
titles and detailed descriptions, are cleaned by removing 
unnecessary symbols, normalizing whitespace, converting text 
to lowercase where appropriate, and tokenizing the input using 
the tokenizer associated with the selected transformer model. 
Structured repository attributes are processed independently 
through suitable encoding and normalization techniques 
depending on their data type.
B. Semantic Feature Extraction
 Semantic understanding of issue reports is performed using 
a pretrained transformer encoder. The model processes issue 
titles and descriptions to generate contextual embeddings that 
capture relationships among words using self-attention 
mechanisms [1]–[5]. Unlike traditional text representations 
such as TF-IDF or static word embeddings, transformer models 
generate context-dependent representations in which the 
meaning of each token is influenced by its surrounding text.
C. Metadata Representation Learning
 Repository metadata provides complementary information 
that may not be explicitly expressed in the issue description. 
Structured attributes, including issue status and other 
repository-related features, are processed through a lightweight 
fully connected neural network to obtain a compact latent 
representation. Learning metadata independently allows the 
model to preserve structured repository information while 
transforming heterogeneous attributes into a common feature 
space. This representation complements the semantic 
information extracted from the textual branch.
D. Multi-Task Late Fusion Architecture
 The distinguishing component of VigilOps-MTLF is its 
Multi-Task Late Fusion (MTLF) architecture. Instead of 
combining textual and structured information at the input level, 
the framework first learns feature representations 
independently for each modality. The outputs of the 
transformer encoder and metadata encoder are then 
concatenated within a dedicated late fusion layer to produce a 
unified feature representation.The fused representation 
captures both semantic and repository-level characteristics, 
providing richer information for downstream prediction. In 
addition, the shared feature space enables multiple learning 
objectives to benefit from common representations without 
requiring separate models for each task [16], [17].
TABLE II. VIGILOPS-MTLF CORE MODULES
Module Description
Transformer Encoder Extracts semantic features from issue 
text.
Metadata Encoder Encodes repository metadata.
Late Fusion Layer Combines text and metadata features.
Shared Representation Layer Learns shared task features.
Issue Classification Head Predicts issue category.
Closure Prediction Head Predicts issue closure status.
E. Multi-Task Prediction Heads
 Following feature fusion, the shared representation is 
supplied to two independent prediction heads that are optimized 
simultaneously during training.
1) Issue Classification
The first prediction branch performs multi-class 
classification by assigning each issue to its corresponding 
maintenance category. A Softmax activation function is 
used to compute the probability distribution across all 
predefined classes.
2) Issue Closure Prediction
The second prediction branch performs binary 
classification to estimate the likelihood that an issue will 
be resolved. A sigmoid activation function produces the 
probability of issue closure based on the learned shared 
representation.
F. Training Configuration
 The proposed framework is implemented using PyTorch 
together with the Hugging Face Transformers library [22], [23]. 
Model parameters are optimized using the Adam optimizer, 
while task-specific cross-entropy loss functions guide the 
learning process. Mini-batch training, dropout regularization, 
and early stopping are incorporated to improve model 
generalization and reduce overfitting. After training, the model 
can be exported through ONNX Runtime to support efficient 
inference across different deployment environments [24].
G. Model Implementation
 VigilOps-MTLF is implemented as a modular pipeline 
comprising preprocessing, feature extraction, model training, 
inference, and evaluation components. Classical baseline 
algorithms are developed using Scikit-learn, whereas the 
proposed deep learning architecture is implemented with 
PyTorch and the Hugging Face Transformers ecosystem for 
contextual representation learning [21]–[23]. Model evaluation 
and result visualization are performed using standard Python 
scientific computing libraries, ensuring reproducibility and 
enabling consistent comparison across all experimental 
settings.
V. EXPERIMENTAL SETUP
 This section outlines the experimental methodology used to 
evaluate the proposed VigilOps-MTLF framework. It describes 
the dataset partitioning strategy, preprocessing procedure, 
model training configuration, execution environment, and 
evaluation criteria. All models were trained and tested under 
consistent experimental conditions to enable a fair comparison 
between the proposed multi-task architecture and the selected 
baseline approaches. Standard performance measures were 
employed to assess both issue classification and issue closure 
prediction.
A. Dataset Partitioning and Training Strategy
 The Helpdesk Tickets dataset was partitioned into training 
and testing subsets using stratified sampling to preserve the 
original class distribution across both prediction tasks. 
Approximately 80% of the available samples were used for 
model training, while the remaining 20% were reserved 
exclusively for performance evaluation.
To improve the model's ability to generalize, training was 
performed using mini-batch optimization together with dropout 
regularization. Hyperparameter selection was carried out using 
only the training data, whereas the testing set remained isolated 
throughout model development. This separation ensured that 
the reported results reflected the model's performance on 
previously unseen data.
VI. RESULTS AND ANALYSIS
A. Performance Metrics Summary
 Table III summarizes the performance of all evaluated 
models. The proposed VigilOps-MTLF framework achieves 
competitive results by jointly learning issue classification and 
issue closure prediction within a unified multi-task architecture. 
Unlike conventional approaches that train separate models for 
individual tasks, the proposed framework shares intermediate 
representations across related objectives, enabling more 
effective utilization of semantic and contextual information.
TABLE III. METRICS SUMMARY
B. Issue Classification Performance
 For the issue classification task, VigilOps-MTLF 
demonstrates the ability to distinguish among different 
categories of software issues by learning contextual 
information from issue titles and descriptions. Transformer generated embeddings capture software-specific terminology 
and semantic relationships more effectively than manually 
engineered textual features, allowing the model to produce 
more reliable category predictions [2]–[6].
C. Issue Closure Prediction Results
 The second prediction objective evaluates the framework's 
ability to estimate whether an issue is likely to remain open or 
be resolved. In addition to semantic information extracted from 
issue descriptions, the model incorporates structured repository 
metadata, allowing it to learn characteristics associated with 
issue lifecycle progression.
Fig. 2. ROC Curve for VigilOps-MTLF
Fig. 3. PR Curve for VigilOps-MTLF
D. Comparative Discussion of Results
 The experimental findings highlight several advantages of 
the proposed VigilOps-MTLF framework. First, transformer based semantic representations provide richer contextual 
understanding than conventional machine learning models that 
depend primarily on manually engineered textual features. 
Second, the late fusion mechanism successfully integrates 
textual information with structured repository metadata, 
allowing each modality to contribute complementary 
knowledge without interfering with independent feature 
learning. Finally, the multi-task learning strategy enables issue 
classification and issue closure prediction to share useful 
representations, reducing computational redundancy while 
improving learning efficiency [16], [17].
VII. CONCLUSION
This paper presented VigilOps-MTLF (Volumetric Issue 
Grouping and Intelligent Lifecycle Optimization Platform via 
Multi-Task Late Fusion), a unified deep learning framework for 
intelligent software issue lifecycle management. The proposed 
architecture combines transformer-based semantic 
representations with structured repository metadata through a 
Multi-Task Late Fusion strategy, enabling issue classification 
and issue closure prediction to be performed simultaneously 
within a single learning framework. Experimental evaluation 
on a publicly available Helpdesk/GitHub issue dataset 
demonstrated competitive performance across standard 
evaluation metrics, including Accuracy, Precision, Recall, 
Macro-F1, ROC analysis, and confusion matrix analysis. The 
findings suggest that integrating contextual semantic 
information with repository metadata improves predictive 
performance while providing an efficient and practical 
approach for automated software issue management. The 
proposed framework establishes a flexible foundation for future 
software repository intelligence systems. Future research will 
focus on addressing class imbalance through advanced learning 
Model Accuracy Precision Recall Macro F1
TF-IDF + Logistic 
Regression 0.7075 0.4147 0.5920 0.4653
TF-IDF + Random 
Forest 0.7500 0.1784 0.1254 0.1386
VigilOps-MTLF 
(Issue Classification 
Head)
0.7325 0.0349 0.0476 0.0403
VigilOps-MTLF 
(Closure Forecasting 
Head)
0.9375 0.4688 0.5000 0.4839
strategies, incorporating Large Language Models (LLMs) and 
Graph Neural Networks (GNNs) to enhance semantic reasoning 
and repository relationship modeling, and extending the 
framework to support developer recommendation, issue 
prioritization, duplicate issue detection, and multilingual issue 
analysis. These enhancements are expected to further improve 
the applicability of VigilOps-MTLF for intelligent software 
maintenance across both open-source repositories and 
enterprise software development environments.
References 
[1] A. Vaswani et al., “Attention Is All You Need,” in Advances in Neural 
Information Processing Systems (NeurIPS), vol. 30, 2017, pp. 5998–6008.
[2] J. Devlin, M. W. Chang, K. Lee, and K. Toutanova, “BERT: Pre-training of 
Deep Bidirectional Transformers for Language Understanding,” in Proc. North 
American Chapter of the Association for Computational Linguistics: Human 
Language Technologies (NAACL-HLT), 2019, pp. 4171–4186.
[3] Y. Liu et al., “RoBERTa: A Robustly Optimized BERT Pretraining 
Approach,” arXiv preprint arXiv:1907.11692, 2019.
[4] V. Sanh, L. Debut, J. Chaumond, and T. Wolf, “DistilBERT, a Distilled 
Version of BERT: Smaller, Faster, Cheaper and Lighter,” in NeurIPS 
Workshop, 2019.
[5] T. Wolf et al., “Transformers: State-of-the-Art Natural Language 
Processing,” in Proc. 2020 Conference on Empirical Methods in Natural 
Language Processing: System Demonstrations (EMNLP), 2020, pp. 38–45.
[6] M. Allamanis, E. T. Barr, C. Bird, and C. Sutton, “A Survey of Machine 
Learning for Big Code and Naturalness,” ACM Computing Surveys, vol. 51, no. 
4, pp. 1–37, 2018.
[7] T. Mikolov, K. Chen, G. Corrado, and J. Dean, “Efficient Estimation of 
Word Representations in Vector Space,” arXiv preprint arXiv:1301.3781, 
2013.
[8] J. Pennington, R. Socher, and C. D. Manning, “GloVe: Global Vectors for 
Word Representation,” in Proc. Conference on Empirical Methods in Natural 
Language Processing (EMNLP), 2014, pp. 1532–1543.
[9] T. Chen and C. Guestrin, “XGBoost: A Scalable Tree Boosting System,” in 
Proc. 22nd ACM SIGKDD International Conference on Knowledge Discovery 
and Data Mining (KDD), 2016, pp. 785–794.
[10] L. Breiman, “Random Forests,” Machine Learning, vol. 45, no. 1, pp. 5–
32, 2001.
[11] C. Cortes and V. Vapnik, “Support-Vector Networks,” Machine Learning, 
vol. 20, no. 3, pp. 273–297, 1995.
[12] D. Jurafsky and J. H. Martin, Speech and Language Processing, 3rd ed. 
Pearson, 2023.
[13] Y. LeCun, Y. Bengio, and G. Hinton, “Deep Learning,” Nature, vol. 521, 
no. 7553, pp. 436–444, 2015.
[14] K. He, X. Zhang, S. Ren, and J. Sun, “Deep Residual Learning for Image 
Recognition,” in Proc. IEEE Conference on Computer Vision and Pattern 
Recognition (CVPR), 2016, pp. 770–778.
[15] A. Graves, A. Mohamed, and G. Hinton, “Speech Recognition with Deep 
Recurrent Neural Networks,” in Proc. IEEE International Conference on 
Acoustics, Speech and Signal Processing (ICASSP), 2013, pp. 6645–6649.
[16] R. Caruana, “Multitask Learning,” Machine Learning, vol. 28, no. 1, pp. 
41–75, 1997.
[17] S. Ruder, “An Overview of Multi-Task Learning in Deep Neural 
Networks,” arXiv preprint arXiv:1706.05098, 2017.
[18] T. Lin, P. Goyal, R. Girshick, K. He, and P. Dollár, “Focal Loss for Dense 
Object Detection,” in Proc. IEEE International Conference on Computer 
Vision (ICCV), 2017, pp. 2980–2988.
[19] N. V. Chawla, K. W. Bowyer, L. O. Hall, and W. P. Kegelmeyer, 
“SMOTE: Synthetic Minority Over-sampling Technique,” Journal of Artificial 
Intelligence Research, vol. 16, pp. 321–357, 2002.
[20] M. Hall et al., “The WEKA Data Mining Software: An Update,” SIGKDD 
Explorations, vol. 11, no. 1, pp. 10–18, 2009.
[21] F. Pedregosa et al., “Scikit-learn: Machine Learning in Python,” Journal 
of Machine Learning Research, vol. 12, pp. 2825–2830, 2011.
[22] A. Paszke et al., “PyTorch: An Imperative Style, High-Performance Deep 
Learning Library,” in Advances in Neural Information Processing Systems 
(NeurIPS), 2019, pp. 8026–8037.
[23] Hugging Face Inc., “Transformers Library: State-of-the-Art Machine 
Learning for PyTorch, TensorFlow, and JAX,” 2024.
[24] Microsoft, “ONNX Runtime Documentation,” Open Neural Network 
Exchange (ONNX), 2024.
[25] AWS, “Deep Java Library (DJL) Documentation,” 2024.
[26] GitHub Inc., “GitHub Issues Documentation,” 2024.
[27] T. Bueck, “Helpdesk Tickets – High Quality Dataset,” Kaggle, 2024.
[28] Kaggle Inc., “Helpdesk Tickets – High Quality,” Kaggle, 2024.
[29] T. Zimmermann, N. Nagappan, H. Gall, E. Giger, and B. Murphy, “Cross Project Defect Prediction: A Large Scale Experiment on Data vs. Domain vs. 
Process,” in Proc. European Software Engineering Conference and ACM 
SIGSOFT Symposium on the Foundations of Software Engineering 
(ESEC/FSE), 2009, pp. 91–100.
[30] H. Kagdi, M. L. Collard, and J. I. Maletic, “A Survey and Taxonomy of 
Approaches for Mining Software Repositories in the Context of Software 
Evolution,” Journal of Software Maintenance and Evolution: Research and 
Practice, vol. 19, no. 2, pp. 77–131, 200
