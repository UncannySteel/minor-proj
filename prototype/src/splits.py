"""Stage 4 - Evaluation protocol.

One protocol: the competition's own train/test split. The test file is used as
shipped and is never touched during training or model selection, which is what
makes these numbers comparable to published NLBSE'23 results rather than to a
split we invented for ourselves.

A validation slice is carved out of train, stratified on the label, and is used
only for early stopping.

Note there is deliberately no home-made random split reported alongside. Adding
one would invite comparing a number against a differently-constructed number,
and the benchmark protocol is the one that means anything to a reader.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

import config


def build_split(train_df: pd.DataFrame, test_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    try:
        tr, va = train_test_split(
            train_df,
            test_size=config.VAL_SIZE,
            random_state=config.SEED,
            stratify=train_df["y"],
        )
    except ValueError as exc:
        print(f"[split] stratification unavailable ({exc}) - splitting unstratified")
        tr, va = train_test_split(train_df, test_size=config.VAL_SIZE, random_state=config.SEED)

    parts = {
        "train": tr.reset_index(drop=True),
        "val": va.reset_index(drop=True),
        "test": test_df.reset_index(drop=True),
    }
    print(
        f"[split] official NLBSE'23 protocol | train {len(parts['train']):,} | "
        f"val {len(parts['val']):,} | test {len(parts['test']):,} (held out, untouched)"
    )
    return parts


def class_weights(y: np.ndarray, n_classes: int) -> np.ndarray:
    """Inverse-frequency weights, so the rare classes are not simply ignored.

    The label set is genuinely imbalanced - `bug` and `feature` together are
    roughly 90% of the data, `documentation` under 5%. Unweighted, the loss is
    minimised by ignoring the tail, which scores well on accuracy and badly on
    Macro-F1. Weighting is why the tail classes get learned at all.
    """
    counts = np.bincount(y, minlength=n_classes).astype("float64")
    counts[counts == 0] = 1.0
    w = counts.sum() / (n_classes * counts)
    return w.astype("float32")
