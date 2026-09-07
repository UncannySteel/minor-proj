"""Stage 5 - Classical baselines.

The proposed model has to beat something. These are the cheap rungs of the
ladder the literature recommends:

    majority        predict the most frequent class. The floor, and the reason
                    Macro-F1 is reported: on this label set `bug` alone scores
                    over 50% accuracy while scoring ~0.17 Macro-F1.
    tfidf+lr        TF-IDF over title+body, logistic regression. The standard
                    strong-cheap text baseline.
    tfidf+svm       same features, linear SVM. Usually a shade better and much
                    faster to fit on sparse high-dimensional input.
    metadata-only   logistic regression on the structural features alone, no
                    text at all. This is the important one: it establishes how
                    much of the task is solvable from shape and provenance
                    ("long body, has a stack trace, author is a drive-by"),
                    which is exactly what the fusion branch is supposed to add.

All four are fitted on train and scored on the official held-out test file.
"""

from __future__ import annotations

import time

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

import config
from src import evaluate
from src.features import META_FEATURES

N_CLASSES = len(config.ISSUE_CLASSES)


def _tfidf():
    return TfidfVectorizer(
        max_features=50_000,
        ngram_range=(1, 2),
        min_df=2,
        sublinear_tf=True,
        strip_accents="unicode",
    )


def run_baselines(parts: dict, table: evaluate.ResultsTable) -> None:
    train, test = parts["train"], parts["test"]
    y_train = train["y"].to_numpy()
    y_test = test["y"].to_numpy()

    x_train = train["text"].tolist()
    x_test = test["text"].tolist()

    # -- majority class -----------------------------------------------------
    majority = int(np.bincount(y_train, minlength=N_CLASSES).argmax())
    table.add(
        "majority class",
        evaluate.compute_metrics(y_test, np.full_like(y_test, majority), N_CLASSES),
        f"always predicts `{config.ISSUE_CLASSES[majority]}`",
    )

    # -- TF-IDF text models -------------------------------------------------
    t0 = time.time()
    vec = _tfidf()
    xt_train = vec.fit_transform(x_train)
    xt_test = vec.transform(x_test)
    print(f"[baselines] TF-IDF: {xt_train.shape[1]:,} features in {time.time() - t0:.0f}s")

    t0 = time.time()
    lr = LogisticRegression(max_iter=1000, class_weight="balanced").fit(xt_train, y_train)
    pred_lr = lr.predict(xt_test)
    table.add(
        "TF-IDF + LogisticRegression",
        evaluate.compute_metrics(y_test, pred_lr, N_CLASSES),
        f"text only, fitted in {time.time() - t0:.0f}s",
    )
    evaluate.plot_confusion(y_test, pred_lr, "TF-IDF + LogisticRegression")
    evaluate.plot_roc_pr(y_test, lr.predict_proba(xt_test), "TF-IDF + LogisticRegression")

    t0 = time.time()
    svm = LinearSVC(class_weight="balanced").fit(xt_train, y_train)
    table.add(
        "TF-IDF + LinearSVC",
        evaluate.compute_metrics(y_test, svm.predict(xt_test), N_CLASSES),
        f"text only, fitted in {time.time() - t0:.0f}s",
    )

    # -- metadata only ------------------------------------------------------
    scaler = StandardScaler().fit(train[META_FEATURES].to_numpy(dtype="float32"))
    m_train = scaler.transform(train[META_FEATURES].to_numpy(dtype="float32"))
    m_test = scaler.transform(test[META_FEATURES].to_numpy(dtype="float32"))

    clf_m = LogisticRegression(max_iter=1000, class_weight="balanced").fit(m_train, y_train)
    pred_m = clf_m.predict(m_test)
    table.add(
        "metadata-only LogisticRegression",
        evaluate.compute_metrics(y_test, pred_m, N_CLASSES),
        f"{len(META_FEATURES)} structural features, no text at all",
    )
    evaluate.plot_confusion(y_test, pred_m, "metadata-only LogisticRegression")
