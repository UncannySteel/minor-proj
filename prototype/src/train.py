"""Training loop.

Single-task, class-weighted cross-entropy. Weighting matters here: `bug` and
`feature` are roughly 90% of the label mass, and an unweighted loss is happiest
ignoring `question` and `documentation` entirely - which scores well on
accuracy and badly on Macro-F1.

Early stopping watches validation Macro-F1, never accuracy, for the same
reason. The validation slice comes out of train; the competition's test file is
never touched during training or model selection.
"""

from __future__ import annotations

import time

import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

import config
from src import evaluate, model as model_mod, splits as splits_mod
from src.features import META_FEATURES

N_CLASSES = len(config.ISSUE_CLASSES)


def get_device() -> torch.device:
    if torch.cuda.is_available():
        dev = torch.device("cuda")
        print(f"[train] device: cuda ({torch.cuda.get_device_name(0)})")
    else:
        dev = torch.device("cpu")
        print("[train] device: cpu (no CUDA - this will be slow)")
    return dev


def _encode_part(part, tokenizer, scaler, need_text: bool):
    n = len(part)
    if need_text:
        enc = tokenizer(part["text"].tolist())
        ids, mask = enc["input_ids"], enc["attention_mask"]
    else:
        # The metadata-only ablation never reads text; skip tokenisation
        # entirely rather than paying for tensors the model will not touch.
        ids = torch.zeros((n, 1), dtype=torch.long)
        mask = torch.zeros((n, 1), dtype=torch.long)

    meta = torch.tensor(scaler.transform(part[META_FEATURES].to_numpy(dtype="float32")))
    return TensorDataset(ids, mask, meta.float(), torch.tensor(part["y"].to_numpy(), dtype=torch.long))


@torch.no_grad()
def _predict(net, loader, device):
    net.eval()
    logits, ys = [], []
    for ids, mask, meta, y in loader:
        out = net(ids.to(device), mask.to(device), meta.to(device))
        logits.append(out.float().cpu())
        ys.append(y)
    return torch.cat(logits), torch.cat(ys).numpy()


def train_model(
    parts: dict,
    encoder_name: str = "distilbert",
    use_text: bool = True,
    use_meta: bool = True,
    epochs: int | None = None,
    device: torch.device | None = None,
    seed: int = config.SEED,
):
    """Fit on train, early-stop on val, predict the official test file.

    Note on determinism: seeding fixes initialisation, shuffling and dropout,
    but it does not make CUDA training reproducible. Non-deterministic cuDNN
    kernel selection and atomic accumulation in the backward pass mean two runs
    with the same seed land in different places. Measured swing on this setup is
    roughly +/- 0.007 Macro-F1 - larger than the effect the experiment is trying
    to detect, which is why `--seeds` exists.
    """
    torch.manual_seed(seed)
    np.random.seed(seed)

    device = device or get_device()
    epochs = epochs if epochs is not None else config.EPOCHS

    encoder, tokenizer = (model_mod.build_encoder(encoder_name) if use_text else (None, None))
    net = model_mod.FusionIssueClassifier(
        encoder, len(META_FEATURES), use_text=use_text, use_meta=use_meta
    ).to(device)
    print(f"[train] {net.describe()}")

    scaler_meta = StandardScaler().fit(parts["train"][META_FEATURES].to_numpy(dtype="float32"))

    t0 = time.time()
    ds_train = _encode_part(parts["train"], tokenizer, scaler_meta, use_text)
    ds_val = _encode_part(parts["val"], tokenizer, scaler_meta, use_text)
    ds_test = _encode_part(parts["test"], tokenizer, scaler_meta, use_text)
    print(
        f"[train] encoded {len(ds_train):,}/{len(ds_val):,}/{len(ds_test):,} "
        f"in {time.time() - t0:.0f}s"
    )

    dl_train = DataLoader(ds_train, batch_size=config.BATCH_SIZE, shuffle=True)
    dl_val = DataLoader(ds_val, batch_size=config.BATCH_SIZE * 4)
    dl_test = DataLoader(ds_test, batch_size=config.BATCH_SIZE * 4)

    w = splits_mod.class_weights(parts["train"]["y"].to_numpy(), N_CLASSES)
    print(f"[train] class weights: {dict(zip(config.ISSUE_CLASSES, np.round(w, 2)))}")
    criterion = nn.CrossEntropyLoss(weight=torch.tensor(w).to(device))

    lr = config.LEARNING_RATE if (use_text and encoder_name != "gru") else config.LEARNING_RATE_GRU
    opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=config.WEIGHT_DECAY)

    use_amp = device.type == "cuda"
    amp_scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    best_f1, best_state = -1.0, None
    for epoch in range(1, epochs + 1):
        net.train()
        running, seen, started = 0.0, 0, time.time()

        for step, (ids, mask, meta, y) in enumerate(dl_train, 1):
            ids, mask, meta, y = ids.to(device), mask.to(device), meta.to(device), y.to(device)

            opt.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=use_amp):
                loss = criterion(net(ids, mask, meta), y)

            amp_scaler.scale(loss).backward()
            amp_scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            amp_scaler.step(opt)
            amp_scaler.update()

            running += loss.item() * len(y)
            seen += len(y)
            if step % 250 == 0:
                print(
                    f"[train]   epoch {epoch} step {step}/{len(dl_train)} "
                    f"loss {running / seen:.4f} ({time.time() - started:.0f}s)",
                    flush=True,
                )

        logits, y_val = _predict(net, dl_val, device)
        m = evaluate.compute_metrics(y_val, logits.argmax(1).numpy())
        print(
            f"[train] epoch {epoch}  train_loss {running / max(seen, 1):.4f}  "
            f"val acc {m['accuracy']:.4f}  val macroF1 {m['macro_f1']:.4f}  "
            f"({time.time() - started:.0f}s)"
        )

        if m["macro_f1"] > best_f1:
            best_f1 = m["macro_f1"]
            best_state = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
            print(f"[train]   new best (val Macro-F1 {best_f1:.4f}) - checkpointed")

    if best_state is not None:
        net.load_state_dict(best_state)

    logits, y_test = _predict(net, dl_test, device)
    return {
        "y_true": y_test,
        "y_pred": logits.argmax(1).numpy(),
        "y_proba": torch.softmax(logits, dim=1).numpy(),
        "best_val_f1": best_f1,
    }
