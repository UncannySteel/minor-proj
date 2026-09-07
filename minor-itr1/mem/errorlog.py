"""Structured error log: append-only JSONL, one line per failure.

Deliberately not the episodic layer. An exception is a machine fact - noisy,
high-volume, and mostly uninteresting. An episode is a considered note about
something that taught you something. The log is where failures land
automatically; a *recurring* failure is the signal that one of them deserves
promoting into memory by hand, which ``stats()`` surfaces via fingerprints.

    log = ErrorLog(root)
    with log.capture("recall", query=q):     # logs, then re-raises
        hits = recall.search(store, q)

Entries are JSON objects, one per line, so the file stays greppable and
append-safe without a lock::

    {"ts": "...", "kind": "recall", "severity": "error", "type": "ValueError",
     "message": "...", "fingerprint": "9f2a1c04", "context": {...},
     "traceback": "..."}
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import traceback as tb_mod
from collections import Counter
from pathlib import Path

from . import schema

LOG_DIRNAME = "logs"
ERROR_FILE = "errors.jsonl"
MAX_BYTES = 2 * 1024 * 1024
SEVERITIES = ("debug", "info", "warning", "error", "critical")

# Digits, hex blobs, quoted strings and paths vary between occurrences of the
# same bug; strip them so fingerprints group by shape rather than by instance.
_NOISE = (
    (re.compile(r"[A-Za-z]:[\\/][^\s'\"]+"), "<path>"),
    (re.compile(r"(?<![\w])/[^\s'\"]{2,}"), "<path>"),
    (re.compile(r"0x[0-9a-fA-F]+"), "<addr>"),
    (re.compile(r"\b[0-9a-fA-F]{8,}\b"), "<hex>"),
    (re.compile(r"\d+"), "<n>"),
    (re.compile(r"'[^']*'"), "'<s>'"),
)


def fingerprint(kind, exc_type, message):
    """Stable short hash grouping recurrences of the same failure shape."""
    text = str(message or "")
    for pattern, replacement in _NOISE:
        text = pattern.sub(replacement, text)
    key = "%s|%s|%s" % (kind or "", exc_type or "", text.strip().lower())
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]


class ErrorLog:
    def __init__(self, root=None, filename=ERROR_FILE, max_bytes=MAX_BYTES):
        from .store import default_root
        self.root = Path(root or default_root()).resolve()
        self.dir = self.root / LOG_DIRNAME
        self.path = self.dir / filename
        self.max_bytes = max_bytes

    # -- write ----------------------------------------------------------
    def record(self, message, kind="general", severity="error", exc=None,
               traceback_text=None, **context):
        """Append one entry and return it. Never raises: a logger that can
        fail the operation it is logging is worse than no logger."""
        exc_type = type(exc).__name__ if exc is not None else None
        if exc is not None and traceback_text is None:
            traceback_text = "".join(
                tb_mod.format_exception(type(exc), exc, exc.__traceback__)).strip()
        entry = {
            "ts": schema.now_iso(),
            "kind": kind,
            "severity": severity if severity in SEVERITIES else "error",
            "type": exc_type,
            "message": str(message),
            "fingerprint": fingerprint(kind, exc_type, message),
            "context": {k: _plain(v) for k, v in context.items()},
        }
        if traceback_text:
            entry["traceback"] = traceback_text
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            self._rotate_if_needed()
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, sort_keys=False) + "\n")
        except OSError:
            pass
        return entry

    def exception(self, exc, kind="general", **context):
        return self.record(str(exc) or type(exc).__name__, kind=kind,
                           severity="error", exc=exc, **context)

    def capture(self, kind="general", reraise=True, **context):
        """Context manager: log whatever escapes, then re-raise by default."""
        return _Capture(self, kind, reraise, context)

    # -- read -----------------------------------------------------------
    def entries(self, limit=None, kind=None, severity=None, fingerprint=None,
                since=None):
        rows = []
        if not self.path.exists():
            return rows
        cutoff = schema.parse_ts(since) if since else None
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue  # a torn line loses one entry, not the log
                    if kind and row.get("kind") != kind:
                        continue
                    if severity and row.get("severity") != severity:
                        continue
                    if fingerprint and row.get("fingerprint") != fingerprint:
                        continue
                    if cutoff is not None:
                        stamp = schema.parse_ts(row.get("ts"))
                        if stamp is None or stamp < cutoff:
                            continue
                    rows.append(row)
        except OSError:
            return rows
        return rows[-limit:] if limit else rows

    def stats(self, min_recurrence=3):
        """Counts by kind and severity, plus the fingerprints worth promoting."""
        rows = self.entries()
        groups = {}
        for row in rows:
            key = row.get("fingerprint")
            group = groups.setdefault(key, {"fingerprint": key, "count": 0,
                                            "kind": row.get("kind"),
                                            "type": row.get("type"),
                                            "message": row.get("message"),
                                            "first": row.get("ts"),
                                            "last": row.get("ts")})
            group["count"] += 1
            group["last"] = row.get("ts")
        recurring = sorted((g for g in groups.values() if g["count"] >= min_recurrence),
                           key=lambda g: -g["count"])
        return {
            "total": len(rows),
            "by_kind": dict(Counter(r.get("kind") for r in rows)),
            "by_severity": dict(Counter(r.get("severity") for r in rows)),
            "distinct": len(groups),
            "recurring": recurring,
            "path": str(self.path),
        }

    # -- maintenance ----------------------------------------------------
    def _rotate_if_needed(self):
        try:
            if self.path.exists() and self.path.stat().st_size >= self.max_bytes:
                os.replace(self.path, self.path.with_suffix(".1.jsonl"))
        except OSError:
            pass

    def clear(self):
        try:
            if self.path.exists():
                self.path.unlink()
                return True
        except OSError:
            pass
        return False


class _Capture:
    __slots__ = ("log", "kind", "reraise", "context")

    def __init__(self, log, kind, reraise, context):
        self.log, self.kind, self.reraise, self.context = log, kind, reraise, context

    def __enter__(self):
        return self.log

    def __exit__(self, exc_type, exc, traceback):
        if exc is None:
            return False
        self.log.exception(exc, kind=self.kind, **self.context)
        return not self.reraise


def _plain(value):
    """Context values must survive json.dumps; anything else becomes repr."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    return repr(value)


def render(rows, verbose=False):
    if not rows:
        return "(no errors logged)"
    lines = []
    for row in rows:
        lines.append("%s  %-8s %-10s [%s] %s" % (
            row.get("ts", "?"), row.get("severity", "?"), row.get("kind", "?"),
            row.get("fingerprint", "?"), row.get("message", "")))
        if row.get("context"):
            lines.append("    context: %s" % json.dumps(row["context"], sort_keys=True))
        if verbose and row.get("traceback"):
            lines.extend("    " + line for line in row["traceback"].splitlines())
    return "\n".join(lines)


def render_stats(data, min_recurrence=3):
    lines = ["errors: %d (%d distinct)" % (data["total"], data["distinct"]),
             "log: %s" % data["path"]]
    if data["by_kind"]:
        lines.append("by kind: %s" % ", ".join(
            "%s=%s" % (k, v) for k, v in sorted(data["by_kind"].items())))
    if data["by_severity"]:
        lines.append("by severity: %s" % ", ".join(
            "%s=%s" % (k, v) for k, v in sorted(data["by_severity"].items())))
    if data["recurring"]:
        lines.append("")
        lines.append("recurring (>=%d) - each of these is an episode waiting to"
                     " be written:" % min_recurrence)
        for group in data["recurring"]:
            lines.append("  %sx [%s] %s: %s" % (
                group["count"], group["fingerprint"], group["kind"],
                (group["message"] or "")[:90]))
    return "\n".join(lines)
