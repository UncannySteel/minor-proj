"""Stage 3 - Metadata feature extraction.

Feeds the metadata encoder branch of the late-fusion model. The question the
whole prototype is built to answer is whether these structural signals add
anything on top of what a transformer already reads out of the text, so they
have to be genuinely independent of the text encoder's view - shape, formatting
and provenance rather than vocabulary.

Three families:

    body      length, structure, formatting - does it have a stack trace, a
              code block, a reproduction checklist, a screenshot
    title     length, punctuation, and whether the reporter self-tagged the
              issue (`[BUG]`, `(feature)`)
    author    one-hot over author_association, the only provenance field the
              dataset carries. Whether the reporter is the repository OWNER or
              a drive-by NONE is real, cheap, and not recoverable from prose.

All of it is available the moment the issue is opened. Nothing here depends on
comments, assignment, reactions, or anything else that happens after creation.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

import config

BODY_FEATURES: list[str] = [
    "log_body_chars",
    "log_body_words",
    "log_n_lines",
    "has_code_block",
    "has_traceback",
    "log_n_urls",
    "has_checklist",
    "has_image",
    "log_n_headings",
    "is_from_template",
    "mean_word_len",
    "log_n_question_marks",
    "has_version_string",
    "upper_ratio",
]

TITLE_FEATURES: list[str] = [
    "log_title_chars",
    "log_title_words",
    "title_has_question_mark",
    "title_upper_ratio",
    "title_has_bracket_tag",
]

AUTHOR_FEATURES: list[str] = [f"author_is_{a.lower()}" for a in config.AUTHOR_ASSOCIATIONS]

META_FEATURES: list[str] = BODY_FEATURES + TITLE_FEATURES + AUTHOR_FEATURES

_CODE_FENCE_RE = re.compile(r"```|^ {4,}\S", re.MULTILINE)
_TRACEBACK_RE = re.compile(
    r"traceback \(most recent call last\)|stack ?trace|exception in thread|"
    r"^\s*at\s+[\w.$]+\(|^\s*File \"",
    re.IGNORECASE | re.MULTILINE,
)
_URL_RE = re.compile(r"https?://\S+")
_CHECKLIST_RE = re.compile(r"^\s*[-*]\s*\[[ xX]\]", re.MULTILINE)
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)
_TEMPLATE_RE = re.compile(
    r"expected behaviou?r|actual behaviou?r|steps to reproduce|"
    r"to reproduce|system information|environment:|version:|describe the bug",
    re.IGNORECASE,
)
_VERSION_RE = re.compile(r"\bv?\d+\.\d+(\.\d+)?\b")
_BRACKET_TAG_RE = re.compile(r"^\s*[\[\(<][^\]\)>]{2,20}[\]\)>]")


def _upper_ratio(text: str) -> float:
    n_alpha = sum(1 for c in text if c.isalpha())
    return (sum(1 for c in text if c.isupper()) / n_alpha) if n_alpha else 0.0


def _row_features(title: str, body: str, author: str) -> dict:
    title = title if isinstance(title, str) else ""
    body = body if isinstance(body, str) else ""

    words = body.split()
    n_words = len(words)
    mean_word_len = (sum(len(w) for w in words) / n_words) if n_words else 0.0

    feats = {
        # body
        "log_body_chars": np.log1p(len(body)),
        "log_body_words": np.log1p(n_words),
        "log_n_lines": np.log1p(body.count("\n")),
        "has_code_block": float(bool(_CODE_FENCE_RE.search(body))),
        "has_traceback": float(bool(_TRACEBACK_RE.search(body))),
        "log_n_urls": np.log1p(len(_URL_RE.findall(body))),
        "has_checklist": float(bool(_CHECKLIST_RE.search(body))),
        "has_image": float(bool(_IMAGE_RE.search(body))),
        "log_n_headings": np.log1p(len(_HEADING_RE.findall(body))),
        "is_from_template": float(bool(_TEMPLATE_RE.search(body))),
        "mean_word_len": mean_word_len,
        "log_n_question_marks": np.log1p(body.count("?")),
        "has_version_string": float(bool(_VERSION_RE.search(body))),
        "upper_ratio": _upper_ratio(body),
        # title
        "log_title_chars": np.log1p(len(title)),
        "log_title_words": np.log1p(len(title.split())),
        "title_has_question_mark": float("?" in title),
        "title_upper_ratio": _upper_ratio(title),
        "title_has_bracket_tag": float(bool(_BRACKET_TAG_RE.search(title))),
    }

    # author association, one-hot
    author = (author or "").strip().upper()
    for a in config.AUTHOR_ASSOCIATIONS:
        feats[f"author_is_{a.lower()}"] = float(author == a)

    return feats


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    rows = [
        _row_features(t, b, a)
        for t, b, a in zip(df["title"], df["body"], df["author_association"])
    ]
    # Explicit column order: the model reads this matrix positionally, so the
    # order must come from META_FEATURES rather than from dict insertion.
    feats = pd.DataFrame(rows, index=df.index, columns=META_FEATURES).astype("float32")
    print(f"[features] built {len(META_FEATURES)} metadata features for {len(df):,} rows")
    return pd.concat([df, feats], axis=1)
