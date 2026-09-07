"""Late-fusion issue classifier.

This is the architecture, in code:

    title + body ---> text encoder --------------------> d_text --+
                      (DistilBERT | BiGRU)                        |
                                                                  +--> concat
    metadata     ---> Dense(64) -> ReLU -> Dense(32) ---> 32 ------+      |
    (25 floats)                                                          v
                                                                      dropout
                                                                         |
                                                              Linear(256) + ReLU
                                                                         |
                                                                 classifier head
                                                          bug / feature / question / documentation

Late fusion, not early: each modality is encoded independently and the two
branches meet only after both have learned their own representation. Whether
that is worth doing is the question the prototype exists to answer, which is
why `use_text` and `use_meta` are constructor flags - the same class produces
the fusion model and both of its ablations, so the comparison is between
identical training code rather than between three hand-written models.

Two text encoders are available. DistilBERT is the default. The BiGRU is a
from-scratch fallback requiring zero downloads: it keeps the pipeline runnable
if a `pip install transformers` or a HuggingFace fetch fails, and it doubles as
a cheap non-transformer rung on the baseline ladder.
"""

from __future__ import annotations

import re
import zlib

import torch
import torch.nn as nn

import config

_TOKEN_RE = re.compile(r"\w+")


# --------------------------------------------------------------------------
# Tokenisers
# --------------------------------------------------------------------------
class HashingTokenizer:
    """Dependency-free tokeniser for the BiGRU encoder.

    Hashes tokens into a fixed vocabulary rather than building one, so there is
    no vocab to fit, persist, or accidentally fit on the test set. Index 0 is
    reserved for padding.
    """

    def __init__(self, vocab_size: int = config.GRU_VOCAB_SIZE, max_len: int = config.MAX_LEN):
        self.vocab_size = vocab_size
        self.max_len = max_len

    def __call__(self, texts: list[str]) -> dict[str, torch.Tensor]:
        n = len(texts)
        ids = torch.zeros((n, self.max_len), dtype=torch.long)
        mask = torch.zeros((n, self.max_len), dtype=torch.long)
        for i, text in enumerate(texts):
            toks = _TOKEN_RE.findall(text or "")[: self.max_len]
            for j, tok in enumerate(toks):
                # crc32, not hash(): Python randomises string hashing per
                # process, which would make runs unreproducible.
                ids[i, j] = (zlib.crc32(tok.encode()) % (self.vocab_size - 1)) + 1
                mask[i, j] = 1
        return {"input_ids": ids, "attention_mask": mask}


class HFTokenizer:
    """Wraps a HuggingFace fast tokenizer into the same call signature."""

    def __init__(self, name: str = config.HF_MODEL_NAME, max_len: int = config.MAX_LEN):
        from transformers import AutoTokenizer

        self.tok = AutoTokenizer.from_pretrained(name)
        self.max_len = max_len

    def __call__(self, texts: list[str]) -> dict[str, torch.Tensor]:
        enc = self.tok(
            [t or "" for t in texts],
            truncation=True,
            padding="max_length",
            max_length=self.max_len,
            return_tensors="pt",
        )
        return {"input_ids": enc["input_ids"], "attention_mask": enc["attention_mask"]}


# --------------------------------------------------------------------------
# Text encoders
# --------------------------------------------------------------------------
class GRUTextEncoder(nn.Module):
    """Embedding -> BiGRU -> masked mean pool. No pretrained weights."""

    def __init__(self):
        super().__init__()
        self.embed = nn.Embedding(config.GRU_VOCAB_SIZE, config.GRU_EMBED_DIM, padding_idx=0)
        self.gru = nn.GRU(
            config.GRU_EMBED_DIM, config.GRU_HIDDEN, batch_first=True, bidirectional=True
        )
        self.out_dim = 2 * config.GRU_HIDDEN

    def forward(self, input_ids, attention_mask):
        h, _ = self.gru(self.embed(input_ids))
        mask = attention_mask.unsqueeze(-1).float()
        return (h * mask).sum(1) / mask.sum(1).clamp(min=1.0)


class BertTextEncoder(nn.Module):
    """DistilBERT, pooled at the [CLS] position (DistilBERT has no pooler head)."""

    def __init__(self, name: str = config.HF_MODEL_NAME):
        super().__init__()
        from transformers import AutoModel

        self.bert = AutoModel.from_pretrained(name)
        self.out_dim = self.bert.config.hidden_size

    def forward(self, input_ids, attention_mask):
        out = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        return out.last_hidden_state[:, 0]


def build_encoder(name: str):
    """Returns (encoder_module, tokenizer). Degrades to the GRU if HF is unavailable."""
    if name == "gru":
        return GRUTextEncoder(), HashingTokenizer()
    try:
        return BertTextEncoder(), HFTokenizer()
    except Exception as exc:  # noqa: BLE001 - any HF failure should degrade, not crash
        print(f"[model] DistilBERT unavailable ({type(exc).__name__}: {exc})")
        print("[model] falling back to the BiGRU encoder - results will differ")
        return GRUTextEncoder(), HashingTokenizer()


# --------------------------------------------------------------------------
class MetadataEncoder(nn.Module):
    def __init__(self, n_features: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, config.META_HIDDEN),
            nn.ReLU(),
            nn.Dropout(config.DROPOUT),
            nn.Linear(config.META_HIDDEN, config.META_OUT),
            nn.ReLU(),
        )
        self.out_dim = config.META_OUT

    def forward(self, x):
        return self.net(x)


# --------------------------------------------------------------------------
class FusionIssueClassifier(nn.Module):
    def __init__(
        self,
        text_encoder: nn.Module | None,
        n_meta_features: int,
        n_classes: int = len(config.ISSUE_CLASSES),
        use_text: bool = True,
        use_meta: bool = True,
    ):
        super().__init__()
        if not (use_text or use_meta):
            raise ValueError("at least one branch must be enabled")

        self.use_text = use_text
        self.use_meta = use_meta

        fused_dim = 0
        if use_text:
            self.text_encoder = text_encoder
            fused_dim += text_encoder.out_dim
        if use_meta:
            self.meta_encoder = MetadataEncoder(n_meta_features)
            fused_dim += self.meta_encoder.out_dim

        self.fusion = nn.Sequential(
            nn.Dropout(config.DROPOUT),
            nn.Linear(fused_dim, config.SHARED_DIM),
            nn.ReLU(),
            nn.Dropout(config.DROPOUT),
        )
        self.head = nn.Linear(config.SHARED_DIM, n_classes)

    def forward(self, input_ids, attention_mask, meta):
        parts = []
        if self.use_text:
            parts.append(self.text_encoder(input_ids, attention_mask))
        if self.use_meta:
            parts.append(self.meta_encoder(meta))

        fused = torch.cat(parts, dim=1) if len(parts) > 1 else parts[0]
        return self.head(self.fusion(fused))

    def describe(self) -> str:
        total = sum(p.numel() for p in self.parameters())
        branches = []
        if self.use_text:
            branches.append(f"text({type(self.text_encoder).__name__}, {self.text_encoder.out_dim}d)")
        if self.use_meta:
            branches.append(f"meta({self.meta_encoder.out_dim}d)")
        return (
            f"FusionIssueClassifier[{' + '.join(branches)} -> {config.SHARED_DIM}d -> "
            f"{len(config.ISSUE_CLASSES)} classes] {total / 1e6:.1f}M params"
        )
