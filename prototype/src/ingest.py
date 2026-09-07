"""Stage 1 - Data acquisition and chunked ingestion.

Downloads the NLBSE'23 issue-report-classification dataset if it is not already
in data/raw/, then reads it in chunks.

The train archive is ~514 MB compressed and expands to well over a gigabyte, so
it is streamed in 100k-row chunks with a random fraction kept from every chunk.
Sampling across the whole file rather than taking the head matters: the CSV is
ordered, and a head-sample would skew both the label mix and the set of
projects represented.

The test file is read in full and never sampled (outside --quick), because it
is the competition's official held-out set and using all of it is what makes
the numbers comparable to published results.
"""

from __future__ import annotations

import argparse
import tarfile
import time
import urllib.request

import numpy as np
import pandas as pd

import config


def download(split: str) -> None:
    """Fetch the archive for `split` into data/raw/ if it is not already there."""
    path = config.ARCHIVES[split]
    if path.exists() and path.stat().st_size > 0:
        print(f"[ingest] {split}: already present ({path.stat().st_size / 1e6:.0f} MB) - {path.name}")
        return

    url = config.DATA_URLS[split]
    print(f"[ingest] {split}: downloading from {url}")
    started = time.time()

    def _progress(block_num, block_size, total_size):
        if total_size > 0 and block_num % 500 == 0:
            done = min(block_num * block_size, total_size)
            print(
                f"[ingest]   {done / 1e6:>6.0f} / {total_size / 1e6:.0f} MB "
                f"({100 * done / total_size:.0f}%)",
                flush=True,
            )

    urllib.request.urlretrieve(url, path, reporthook=_progress)
    print(f"[ingest] {split}: {path.stat().st_size / 1e6:.0f} MB in {time.time() - started:.0f}s")


def _open_csv(split: str):
    """Return a binary file object for the single CSV inside the tar.gz."""
    tf = tarfile.open(config.ARCHIVES[split])
    member = next(m for m in tf.getmembers() if m.name.endswith(".csv"))
    print(f"[ingest] {split}: reading {member.name} ({member.size / 1e6:.0f} MB uncompressed)")
    return tf, tf.extractfile(member)


def read_split(split: str, target_rows: int | None) -> pd.DataFrame:
    """Chunked read. `target_rows=None` reads everything."""
    tf, fh = _open_csv(split)
    try:
        reader = pd.read_csv(
            fh,
            chunksize=config.CHUNK_SIZE,
            on_bad_lines="skip",
            engine="c",
            dtype=str,
        )

        # Estimated total rows, used only to size the sampling fraction.
        universe = 1_200_000 if split == "train" else 142_320
        frac = 1.0 if target_rows is None else min(1.0, (target_rows * 1.15) / universe)

        rng = np.random.default_rng(config.SEED)
        kept, seen, started = [], 0, time.time()

        for i, chunk in enumerate(reader):
            if i == 0:
                missing = [c for c in config.EXPECTED_COLUMNS if c not in chunk.columns]
                if missing:
                    raise SystemExit(
                        f"[ingest] FATAL: expected {config.EXPECTED_COLUMNS}, "
                        f"got {list(chunk.columns)} (missing {missing})"
                    )
                print(f"[ingest] {split}: columns verified {config.EXPECTED_COLUMNS}")
            chunk = chunk[config.EXPECTED_COLUMNS]

            seen += len(chunk)
            if frac >= 1.0:
                kept.append(chunk)
            else:
                mask = rng.random(len(chunk)) < frac
                if mask.any():
                    kept.append(chunk[mask])

            n_kept = sum(len(k) for k in kept)
            if (i + 1) % 3 == 0:
                print(
                    f"[ingest]   {split} chunk {i + 1:>3}  read {seen:>9,}  kept {n_kept:>8,}"
                    f"  ({time.time() - started:.0f}s)",
                    flush=True,
                )
            if target_rows is not None and n_kept >= target_rows * 1.5:
                print(f"[ingest]   {split}: target comfortably met - stopping early")
                break
    finally:
        tf.close()

    df = pd.concat(kept, ignore_index=True) if kept else pd.DataFrame(columns=config.EXPECTED_COLUMNS)
    if target_rows is not None and len(df) > target_rows:
        df = df.sample(n=target_rows, random_state=config.SEED).reset_index(drop=True)

    print(f"[ingest] {split}: read {seen:,} rows, using {len(df):,} ({time.time() - started:.0f}s)")
    return df


def load(quick: bool = False, train_rows: int | None = None):
    for split in ("train", "test"):
        download(split)

    n_train = config.TRAIN_SAMPLE_QUICK if quick else (train_rows or config.TRAIN_SAMPLE)
    n_test = config.TEST_SAMPLE_QUICK if quick else None

    train = read_split("train", n_train)
    test = read_split("test", n_test)
    return train, test


def main() -> None:
    ap = argparse.ArgumentParser(description="Download and sample the NLBSE'23 dataset.")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--train-rows", type=int, default=None)
    args = ap.parse_args()

    train, test = load(quick=args.quick, train_rows=args.train_rows)
    print(f"\ntrain {len(train):,} rows | test {len(test):,} rows")
    print(train["labels"].value_counts())


if __name__ == "__main__":
    main()
