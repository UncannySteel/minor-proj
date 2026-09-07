"""Stage 2 - Data cleaning, normalisation, deduplication and noise removal.

Every filter records rows-in and rows-out into a QualityLog, which is rendered
to results/data_quality.md. A cleaning pipeline whose attrition you cannot see
is a cleaning pipeline you cannot defend, so the report is a first-class
output, not a debug aid.

Three text columns come out:

    title       whitespace-normalised
    body        HTML comments stripped, whitespace normalised, structure intact
                - this is what src/features.py measures, because "has a code
                block" has to be counted before the code block is replaced
    text        title + normalised body with placeholder tokens substituted
                - this is what the models actually read
"""

from __future__ import annotations

import json
import re

import pandas as pd

import config

# --------------------------------------------------------------------------
# Patterns
# --------------------------------------------------------------------------
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
_HASH_RE = re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE)
_NUM_RE = re.compile(r"\b\d[\d.,]*\b")
_WS_RE = re.compile(r"\s+")

_BOT_TITLE_RE = re.compile(
    r"^\s*(?:bump\b|update dependency\b|chore\(deps\)|build\(deps\)|"
    r"\[security\] bump\b|automated\b|\[snyk\])",
    re.IGNORECASE,
)
_BOT_BODY_RE = re.compile(
    r"dependabot|greenkeeper|renovate\[bot\]|snyk\.io|allcontributors\[bot\]",
    re.IGNORECASE,
)

NEAR_DUP_PREFIX_CHARS = 200


# --------------------------------------------------------------------------
class QualityLog:
    """Records the row count before and after each pipeline step."""

    def __init__(self) -> None:
        self.steps: list[dict] = []
        self.notes: list[str] = []

    def record(self, name: str, before: int, after: int, note: str = "") -> None:
        pct = (100.0 * (before - after) / before) if before else 0.0
        self.steps.append(
            {
                "step": name,
                "rows_in": before,
                "rows_out": after,
                "removed": before - after,
                "removed_pct": pct,
                "note": note,
            }
        )
        print(f"[clean] {name:<34} {before:>8,} -> {after:>8,}  (-{before - after:,}, -{pct:.1f}%)")

    def note(self, text: str) -> None:
        self.notes.append(text)

    def save(self, path) -> None:
        """Persist so a cached (--skip-ingest) run can still render the report.

        Without this the attrition table - the main evidence that the cleaning
        happened at all - silently disappears from the report whenever the
        parquet cache is reused.
        """
        path.write_text(json.dumps({"steps": self.steps, "notes": self.notes}, indent=2), "utf-8")

    @classmethod
    def load(cls, path) -> "QualityLog":
        log = cls()
        if path.exists():
            data = json.loads(path.read_text("utf-8"))
            log.steps = data.get("steps", [])
            log.notes = data.get("notes", [])
        return log

    def to_markdown(self, title: str = "Data Quality Report") -> str:
        lines = [
            f"# {title}",
            "",
            "Dataset: **NLBSE'23 Tool Competition, issue report classification** "
            "([source](https://github.com/nlbse2023/issue-report-classification)). "
            "Labels are real GitHub labels applied by project maintainers, and the "
            "train/test split is the competition's own.",
            "",
            "## Pipeline attrition",
            "",
            "| step | rows in | rows out | removed | % removed | note |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
        for s in self.steps:
            lines.append(
                f"| {s['step']} | {s['rows_in']:,} | {s['rows_out']:,} | "
                f"{s['removed']:,} | {s['removed_pct']:.1f}% | {s['note']} |"
            )
        if self.steps:
            first, last = self.steps[0]["rows_in"], self.steps[-1]["rows_out"]
            kept = (100.0 * last / first) if first else 0.0
            lines += ["", f"**Overall: {first:,} rows in -> {last:,} usable ({kept:.1f}% retained).**"]
        if self.notes:
            lines += ["", "## Observations", ""] + [f"- {n}" for n in self.notes]
        return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# Text normalisation
# --------------------------------------------------------------------------
def normalise_text(text: str) -> str:
    """Full normalisation with placeholder substitution - what the models read."""
    if not isinstance(text, str):
        return ""
    text = _FENCED_CODE_RE.sub(" code_block ", text)
    text = _IMAGE_RE.sub(" image_ref ", text)
    text = _INLINE_CODE_RE.sub(" code_span ", text)
    text = _URL_RE.sub(" url_ref ", text)
    text = _EMAIL_RE.sub(" email_ref ", text)
    text = _HASH_RE.sub(" hash_ref ", text)
    text = _NUM_RE.sub(" num ", text)
    text = _WS_RE.sub(" ", text)
    return text.strip().lower()


def _light_normalise(text: str) -> str:
    """Strip HTML comments and collapse runs of whitespace. Structure intact."""
    if not isinstance(text, str):
        return ""
    return _HTML_COMMENT_RE.sub(" ", text).strip()


# --------------------------------------------------------------------------
def clean_frame(df: pd.DataFrame, log: QualityLog, name: str) -> pd.DataFrame:
    df = df.copy()
    prefix = f"[{name}] "

    # 1. Valid label. The output layer is indexed by ISSUE_CLASSES, so anything
    #    outside that vocabulary cannot be represented and must go.
    before = len(df)
    df["labels"] = df["labels"].astype("string").str.strip().str.lower()
    df = df[df["labels"].isin(config.ISSUE_CLASSES)].reset_index(drop=True)
    log.record(prefix + "valid label", before, len(df), f"one of {config.ISSUE_CLASSES}")

    # 2. Null or empty title / body.
    before = len(df)
    df["title"] = df["title"].astype("string")
    df["body"] = df["body"].astype("string")
    df = df[df["title"].notna() & df["body"].notna()]
    df = df[(df["title"].str.strip() != "") & (df["body"].str.strip() != "")]
    df = df.reset_index(drop=True)
    log.record(prefix + "drop null / empty title or body", before, len(df))

    # 3. HTML comments - GitHub issue templates are full of them, and they are
    #    instructions to the human author, never content.
    df["title"] = [_light_normalise(t) for t in df["title"]]
    df["body"] = [_light_normalise(b) for b in df["body"]]
    before = len(df)
    df = df[(df["body"].str.strip() != "") & (df["title"].str.strip() != "")].reset_index(drop=True)
    log.record(prefix + "strip HTML comments", before, len(df), "template boilerplate")

    # 4. Length bounds.
    before = len(df)
    df = df[df["body"].str.len() >= config.MIN_BODY_CHARS].reset_index(drop=True)
    log.record(prefix + "drop bodies under min length", before, len(df), f"< {config.MIN_BODY_CHARS} chars")

    n_trunc = int((df["body"].str.len() > config.MAX_BODY_CHARS).sum())
    df["body"] = df["body"].str.slice(0, config.MAX_BODY_CHARS)
    log.record(prefix + "truncate very long bodies", len(df), len(df), f"{n_trunc:,} truncated")

    # 5. Bot-generated issues. Dependency bumps are machine-written; they would
    #    teach the model a bot's template rather than developer language.
    before = len(df)
    is_bot = df["title"].str.contains(_BOT_TITLE_RE, na=False) | df["body"].str.contains(
        _BOT_BODY_RE, na=False
    )
    df = df[~is_bot].reset_index(drop=True)
    log.record(prefix + "drop bot-generated issues", before, len(df), "dependabot / renovate / snyk")

    # 6. Non-latin-script bodies. DistilBERT is an English uncased model.
    before = len(df)
    non_ascii = df["body"].str.count(r"[^\x00-\x7F]")
    ratio = 1.0 - (non_ascii / df["body"].str.len().clip(lower=1))
    df = df[ratio >= config.MIN_ASCII_RATIO].reset_index(drop=True)
    log.record(prefix + "drop non-english bodies", before, len(df), f"ascii ratio < {config.MIN_ASCII_RATIO:.0%}")

    # 7. Model-facing text: normalised title + normalised body.
    df["text"] = [
        (normalise_text(t) + " " + normalise_text(b)).strip()
        for t, b in zip(df["title"], df["body"])
    ]
    before = len(df)
    df = df[df["text"].str.len() >= config.MIN_BODY_CHARS].reset_index(drop=True)
    log.record(prefix + "normalise + placeholder tokens", before, len(df), "code / url / email / hash / num")

    # 8. Deduplication.
    before = len(df)
    df = df.drop_duplicates(subset=["text"]).reset_index(drop=True)
    log.record(prefix + "exact dedup on normalised text", before, len(df))

    before = len(df)
    df = df[~df["text"].str.slice(0, NEAR_DUP_PREFIX_CHARS).duplicated()].reset_index(drop=True)
    log.record(prefix + f"near-dedup on first {NEAR_DUP_PREFIX_CHARS} chars", before, len(df))

    return df


def drop_train_test_overlap(train: pd.DataFrame, test: pd.DataFrame, log: QualityLog) -> pd.DataFrame:
    """Remove any training row whose text also appears in the official test set.

    Worth checking rather than assuming: an overlap would inflate every score
    reported here, and finding none is itself a result worth stating.
    """
    before = len(train)
    overlap = set(test["text"]) & set(train["text"])
    out = train[~train["text"].isin(overlap)].reset_index(drop=True) if overlap else train
    log.record(
        "drop train rows duplicated in test",
        before,
        len(out),
        f"{len(overlap):,} overlapping texts found" if overlap else "no overlap found",
    )
    return out


def encode_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Map the label string to the fixed integer order declared in config."""
    df = df.copy()
    df["y"] = df["labels"].map({c: i for i, c in enumerate(config.ISSUE_CLASSES)}).astype(int)
    return df
