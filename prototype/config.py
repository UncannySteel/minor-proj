"""Central configuration.

Everything a reviewer would want to change lives here: data sources, the random
seed, sample sizes, and model hyperparameters.
"""

from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results"

for _d in (DATA_RAW, DATA_PROCESSED, RESULTS):
    _d.mkdir(parents=True, exist_ok=True)

TRAIN_PARQUET = DATA_PROCESSED / "train_clean.parquet"
TEST_PARQUET = DATA_PROCESSED / "test_clean.parquet"

QUALITY_REPORT = RESULTS / "data_quality.md"
METRICS_MD = RESULTS / "metrics.md"
METRICS_CSV = RESULTS / "metrics.csv"

# --------------------------------------------------------------------------
# Reproducibility
# --------------------------------------------------------------------------
SEED = 42

# --------------------------------------------------------------------------
# Dataset: NLBSE'23 Tool Competition, issue report classification
#
# https://github.com/nlbse2023/issue-report-classification
#
# Real GitHub labels applied by real maintainers - not derived, not inferred.
# The competition ships its own train/test split, so results here are directly
# comparable to published baselines instead of to a split we invented.
# --------------------------------------------------------------------------
DATA_URLS = {
    "train": "https://tickettagger.blob.core.windows.net/datasets/nlbse23-issue-classification-train.csv.tar.gz",
    "test": "https://tickettagger.blob.core.windows.net/datasets/nlbse23-issue-classification-test.csv.tar.gz",
}
ARCHIVES = {
    "train": DATA_RAW / "nlbse23-train.csv.tar.gz",
    "test": DATA_RAW / "nlbse23-test.csv.tar.gz",
}

EXPECTED_COLUMNS = ["id", "labels", "title", "body", "author_association"]

# The four classes, in fixed order. This ordering is what the model's output
# layer is indexed by, so it must never be derived from the data.
ISSUE_CLASSES = ["bug", "feature", "question", "documentation"]

AUTHOR_ASSOCIATIONS = ["NONE", "CONTRIBUTOR", "OWNER", "MEMBER", "COLLABORATOR", "MANNEQUIN"]

# Published NLBSE'23 baselines on this exact test file, as reported by the
# competition organisers. Micro-averaged F1, which for single-label
# multi-class equals accuracy - so these are directly comparable to the
# accuracy column of our results table.
#
# Both were trained on the FULL ~1.2M-row training set. This prototype samples
# 150k by default, so it is not a like-for-like comparison and the table says
# so. They are here as orientation, not as a target to be gamed.
REFERENCE_BASELINES = [
    ("FastText (competition baseline)", 0.8510),
    ("RoBERTa (competition baseline)", 0.8906),
]

CHUNK_SIZE = 100_000

# Train is ~1.2M rows. A prototype does not need all of it; sampling keeps a
# full run inside a coffee break while leaving the pipeline identical.
TRAIN_SAMPLE = 150_000
TRAIN_SAMPLE_QUICK = 12_000
TEST_SAMPLE_QUICK = 5_000

# --------------------------------------------------------------------------
# Cleaning
# --------------------------------------------------------------------------
MIN_BODY_CHARS = 10
MAX_BODY_CHARS = 20_000
MIN_ASCII_RATIO = 0.90  # crude latin-script filter; DistilBERT is English uncased

# --------------------------------------------------------------------------
# Splits
# --------------------------------------------------------------------------
# The test set is the competition's own held-out file. Only a validation slice
# is carved locally, out of train, and it is used for early stopping alone.
VAL_SIZE = 0.10

# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------
HF_MODEL_NAME = "distilbert-base-uncased"

MAX_LEN = 192
BATCH_SIZE = 32
EPOCHS = 2
EPOCHS_QUICK = 1
LEARNING_RATE = 3e-5
LEARNING_RATE_GRU = 1e-3
WEIGHT_DECAY = 0.01
DROPOUT = 0.3

# Metadata encoder: n_features -> 64 -> 32
META_HIDDEN = 64
META_OUT = 32

# Shared representation after late fusion
SHARED_DIM = 256

# BiGRU fallback encoder (no downloads required)
GRU_VOCAB_SIZE = 30_000
GRU_EMBED_DIM = 128
GRU_HIDDEN = 128

# Persisted alongside the parquet cache so --skip-ingest can still render
# the full attrition table.
QUALITY_LOG_JSON = DATA_PROCESSED / "quality_log.json"


def use_quick_outputs() -> None:
    """Redirect every output path into a `quick/` sandbox.

    A --quick run trains a weaker encoder on a fraction of the data. Letting it
    write to the same files as a full run means one exploratory command silently
    replaces the results you meant to keep - and the parquet cache along with
    them, so the next --skip-ingest run quietly reuses the small sample too.
    Quick runs get their own directory instead.
    """
    global RESULTS, DATA_PROCESSED, TRAIN_PARQUET, TEST_PARQUET
    global QUALITY_REPORT, METRICS_MD, METRICS_CSV, QUALITY_LOG_JSON

    RESULTS = ROOT / "results" / "quick"
    DATA_PROCESSED = ROOT / "data" / "processed" / "quick"
    for _d in (RESULTS, DATA_PROCESSED):
        _d.mkdir(parents=True, exist_ok=True)

    TRAIN_PARQUET = DATA_PROCESSED / "train_clean.parquet"
    TEST_PARQUET = DATA_PROCESSED / "test_clean.parquet"
    QUALITY_LOG_JSON = DATA_PROCESSED / "quality_log.json"
    QUALITY_REPORT = RESULTS / "data_quality.md"
    METRICS_MD = RESULTS / "metrics.md"
    METRICS_CSV = RESULTS / "metrics.csv"
    print(f"[config] --quick: outputs redirected to {RESULTS} (full-run results untouched)")
