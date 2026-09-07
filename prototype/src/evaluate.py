"""Stage 7 - Metrics, tables and figures.

Accuracy is reported alongside macro precision / recall / F1 and MCC, because
on this label set accuracy alone is misleading: `bug` and `feature` are ~90% of
the data, so a model that never predicts `question` or `documentation` still
looks respectable on accuracy and collapses on Macro-F1.

A note on comparability: the NLBSE'23 competition ranks entries on
micro-averaged F1. For single-label multi-class classification micro-F1 is
arithmetically identical to accuracy, so the accuracy column here is directly
comparable to published competition numbers - it is not reported twice under
two names.

Outputs:
    results/metrics.md          paste-ready markdown table
    results/metrics.csv         same numbers, machine readable
    results/confusion_*.png     one per model
    results/roc_*.png           one-vs-rest ROC per class
    results/pr_*.png            one-vs-rest precision-recall per class
"""

from __future__ import annotations

import re

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    auc,
    classification_report,
    confusion_matrix,
    matthews_corrcoef,
    precision_recall_curve,
    precision_recall_fscore_support,
    roc_curve,
)

import config

CLASSES = config.ISSUE_CLASSES
N_CLASSES = len(CLASSES)


def compute_metrics(y_true, y_pred, n_classes: int = N_CLASSES) -> dict:
    labels = list(range(n_classes))
    p, r, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average="macro", zero_division=0
    )
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(p),
        "recall_macro": float(r),
        "macro_f1": float(f1),
        "mcc": float(matthews_corrcoef(y_true, y_pred)),
    }


def per_class_f1(y_true, y_pred) -> dict:
    _, _, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=list(range(N_CLASSES)), average=None, zero_division=0
    )
    return {c: float(v) for c, v in zip(CLASSES, f1)}


class ResultsTable:
    """One row per model, all scored on the official held-out test file."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, model: str, metrics: dict, note: str = "", per_class: dict | None = None) -> None:
        row = {"model": model, **metrics, "note": note}
        if per_class:
            row.update({f"f1_{k}": v for k, v in per_class.items()})
        self.rows.append(row)
        print(
            f"[eval] {model:<36} acc {metrics['accuracy']:.4f}  "
            f"macroF1 {metrics['macro_f1']:.4f}  mcc {metrics['mcc']:.4f}  {note}"
        )

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)

    def write(self, extra: str = "") -> None:
        df = self.frame()
        df.to_csv(config.METRICS_CSV, index=False)

        lines = [
            "# Issue Report Classification - Prototype Results",
            "",
            "Dataset: **NLBSE'23 Tool Competition** issue report classification "
            "([source](https://github.com/nlbse2023/issue-report-classification)). "
            "Labels are real GitHub labels applied by project maintainers.",
            "",
            "All models are fitted on the training file and scored on the "
            "competition's **official held-out test file**, which is never seen "
            "during training or model selection.",
            "",
            "> The NLBSE'23 ranking metric is micro-averaged F1. For single-label "
            "multi-class classification that is arithmetically identical to accuracy, "
            "so the accuracy column below is directly comparable to published "
            "competition results.",
            "",
            "| model | accuracy | precision (macro) | recall (macro) | **Macro-F1** | MCC | note |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
        for _, r in df.iterrows():
            lines.append(
                f"| {r['model']} | {r['accuracy']:.4f} | {r['precision_macro']:.4f} | "
                f"{r['recall_macro']:.4f} | **{r['macro_f1']:.4f}** | {r['mcc']:.4f} | {r['note']} |"
            )

        f1_cols = [c for c in df.columns if c.startswith("f1_")]
        if f1_cols:
            lines += [
                "",
                "## Per-class F1",
                "",
                "Where the macro average actually comes from. `question` and "
                "`documentation` are the minority classes and are where models "
                "differ most.",
                "",
                "| model | " + " | ".join(c[3:] for c in f1_cols) + " |",
                "| --- | " + " | ".join("---:" for _ in f1_cols) + " |",
            ]
            for _, r in df.iterrows():
                if pd.isna(r.get(f1_cols[0])):
                    continue
                cells = " | ".join(f"{r[c]:.4f}" for c in f1_cols)
                lines.append(f"| {r['model']} | {cells} |")

        lines += ["", _reference_section(df)]

        if extra:
            lines += ["", extra]

        config.METRICS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[eval] wrote {config.METRICS_MD}")
        print(f"[eval] wrote {config.METRICS_CSV}")


def _reference_section(df: pd.DataFrame) -> str:
    """Published competition results, for orientation - not a like-for-like race."""
    best = df.loc[df["accuracy"].idxmax()] if not df.empty else None
    lines = [
        "## Published NLBSE'23 baselines, for context",
        "",
        "Reported by the competition organisers on **this exact test file**, in "
        "micro-averaged F1 (= accuracy):",
        "",
        "| system | accuracy / micro-F1 |",
        "| --- | ---: |",
    ]
    for name, score in config.REFERENCE_BASELINES:
        lines.append(f"| {name} | {score:.4f} |")
    if best is not None:
        lines.append(f"| **{best['model']}** (this prototype) | **{best['accuracy']:.4f}** |")

    lines += [
        "",
        "**This is not a like-for-like comparison and should not be presented as one.** "
        "Both published baselines were trained on the full ~1.2M-row training set; this "
        "prototype samples a fraction of it and trains for two epochs with no "
        "hyperparameter search. RoBERTa is also a substantially larger model than "
        "DistilBERT. The numbers are here as orientation - they say whether the pipeline "
        "is in the right neighbourhood, not whether it wins.",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------
_UNSAFE_RE = re.compile(r"[^a-z0-9]+")


def _slug(name: str) -> str:
    """Filename-safe slug.

    Whitelist rather than blacklist. A colon slipping through here is not a
    cosmetic problem on Windows: `foo:bar.png` is parsed as an NTFS alternate
    data stream, so matplotlib writes a zero-byte `foo` and the figure is
    silently lost.
    """
    return _UNSAFE_RE.sub("-", name.lower()).strip("-")


def plot_confusion(y_true, y_pred, model: str):
    cm = confusion_matrix(y_true, y_pred, labels=list(range(N_CLASSES)))
    with np.errstate(divide="ignore", invalid="ignore"):
        norm = np.nan_to_num(cm / cm.sum(axis=1, keepdims=True))

    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    im = ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(N_CLASSES), CLASSES, rotation=30, ha="right")
    ax.set_yticks(range(N_CLASSES), CLASSES)
    ax.set_xlabel("predicted")
    ax.set_ylabel("true")
    ax.set_title(f"{model}\nrow-normalised confusion matrix", fontsize=10)

    for i in range(N_CLASSES):
        for j in range(N_CLASSES):
            ax.text(
                j, i, f"{cm[i, j]:,}\n{norm[i, j]:.0%}",
                ha="center", va="center", fontsize=8,
                color="white" if norm[i, j] > 0.5 else "black",
            )

    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    path = config.RESULTS / f"confusion_{_slug(model)}.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def plot_roc_pr(y_true, y_proba, model: str):
    """One-vs-rest ROC and precision-recall, one curve per class."""
    y_true = np.asarray(y_true)
    y_proba = np.asarray(y_proba)
    if y_proba.ndim != 2 or y_proba.shape[1] != N_CLASSES:
        print("[eval] skipping ROC/PR - probability matrix has unexpected shape")
        return

    fig, ax = plt.subplots(figsize=(5.4, 4.8))
    aucs = []
    for i, cls in enumerate(CLASSES):
        binary = (y_true == i).astype(int)
        if binary.sum() == 0:
            continue
        fpr, tpr, _ = roc_curve(binary, y_proba[:, i])
        a = auc(fpr, tpr)
        aucs.append(a)
        ax.plot(fpr, tpr, lw=1.8, label=f"{cls} (AUC {a:.3f})")
    ax.plot([0, 1], [0, 1], "--", lw=1, color="#999", label="chance")
    ax.set_xlabel("false positive rate")
    ax.set_ylabel("true positive rate")
    ax.set_title(f"ROC, one-vs-rest - {model}\nmacro AUC {np.mean(aucs):.3f}", fontsize=10)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(config.RESULTS / f"roc_{_slug(model)}.png", dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.4, 4.8))
    for i, cls in enumerate(CLASSES):
        binary = (y_true == i).astype(int)
        if binary.sum() == 0:
            continue
        prec, rec, _ = precision_recall_curve(binary, y_proba[:, i])
        ax.plot(rec, prec, lw=1.8, label=f"{cls} (AP {auc(rec, prec):.3f}, base {binary.mean():.3f})")
    ax.set_xlabel("recall")
    ax.set_ylabel("precision")
    ax.set_title(f"Precision-Recall, one-vs-rest - {model}", fontsize=10)
    ax.legend(loc="upper right", fontsize=7)
    fig.tight_layout()
    fig.savefig(config.RESULTS / f"pr_{_slug(model)}.png", dpi=140)
    plt.close(fig)
    print(f"[eval] wrote roc_{_slug(model)}.png and pr_{_slug(model)}.png")


def per_class_report(y_true, y_pred) -> str:
    return classification_report(
        y_true, y_pred, labels=list(range(N_CLASSES)), target_names=CLASSES, zero_division=0
    )
