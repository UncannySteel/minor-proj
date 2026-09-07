"""Index build: a machine index for recall, a Markdown index for humans.

``index/index.json`` holds one entry per record with its term frequencies and
the corpus document frequencies, so recall never has to re-read the store.
``index/MEMORY.md`` is the same content as a browsable table of contents.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from . import schema
from .store import Store

INDEX_FILE = "index.json"
MEMORY_FILE = "MEMORY.md"

STOPWORDS = frozenset("""
a an the and or but if then than that this these those there here of in on at to for from by with
without into over under again further once is are was were be been being am do does did doing have
has had having it its as not no nor so too very can will just should now about after before between
i you he she they we me my your our their them his her him us who whom which what when where why how
""".split())

_TOKEN = re.compile(r"[a-z0-9][a-z0-9_.+-]*")


def tokenize(text):
    """Lowercase word tokens, stopped and length-filtered."""
    return [t for t in _TOKEN.findall(str(text).lower())
            if len(t) > 2 and t not in STOPWORDS]


def record_terms(record):
    """Title counts triple, tags double: both are deliberate labels."""
    counts = Counter()
    counts.update(tokenize(record.title) * 3)
    for tag in record.tags:
        counts.update(tokenize(tag) * 2)
    for field in ("trigger", "subject", "kind"):
        if record.meta.get(field):
            counts.update(tokenize(record.meta[field]))
    counts.update(tokenize(record.body))
    return counts


def build(store, include_archived=False):
    """Walk the store and return the index payload."""
    entries, df = [], Counter()
    for record in store.records(include_archived=include_archived):
        terms = record_terms(record)
        df.update(terms.keys())
        entries.append({
            "id": record.id,
            "layer": record.layer,
            "title": record.title,
            "path": store.relpath(record.path),
            "tags": [str(t).lower() for t in record.tags],
            "links": record.links,
            "created": record.meta.get("created"),
            "occurred": record.meta.get("occurred") or record.meta.get("updated"),
            "updated": record.meta.get("updated"),
            "status": record.meta.get("status", "active"),
            "outcome": record.meta.get("outcome"),
            "kind": record.meta.get("kind"),
            "salience": _unit(record.meta.get("salience"), 0.5),
            "confidence": _unit(record.meta.get("confidence"), 0.5),
            "runs": int(record.meta.get("runs") or 0),
            "successes": int(record.meta.get("successes") or 0),
            "failures": int(record.meta.get("failures") or 0),
            "length": sum(terms.values()),
            "terms": dict(terms),
            "summary": summarize(record),
        })
    lengths = [e["length"] for e in entries] or [1]
    return {
        "generated": schema.now_iso(),
        "count": len(entries),
        "counts_by_layer": dict(Counter(e["layer"] for e in entries)),
        "avg_length": sum(lengths) / len(lengths),
        "df": dict(df),
        "records": entries,
    }


def _unit(value, fallback):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return fallback
    return min(1.0, max(0.0, out))


def summarize(record, limit=160):
    """First real prose line of the body, for index listings and snippets."""
    for raw in record.body.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ">", "|", "---")):
            continue
        line = line.lstrip("-*0123456789. ").strip()
        if len(line) > 3 and not line.startswith("<"):
            return line[:limit] + ("..." if len(line) > limit else "")
    return ""


def save(store, data=None, include_archived=False):
    data = data or build(store, include_archived=include_archived)
    store.index_dir.mkdir(parents=True, exist_ok=True)
    (store.index_dir / INDEX_FILE).write_text(
        json.dumps(data, indent=2, sort_keys=False), encoding="utf-8")
    (store.index_dir / MEMORY_FILE).write_text(
        render_memory_md(data), encoding="utf-8")
    return data


def is_stale(store, data):
    """True when any record file is newer than the stored index."""
    generated = schema.parse_ts(data.get("generated"))
    if generated is None:
        return True
    stamp = generated.timestamp()
    for path in store.paths():
        try:
            if path.stat().st_mtime > stamp + 1:
                return True
        except OSError:
            return True
    return len(list(store.paths())) != data.get("count", -1)


def load(store, rebuild_if_stale=True):
    path = store.index_dir / INDEX_FILE
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = None
        if data and not (rebuild_if_stale and is_stale(store, data)):
            return data
    return build(store)


_LAYER_BLURB = {
    "episodic": "What happened, timestamped. Decays unless promoted.",
    "semantic": "What is true, until something supersedes it.",
    "procedural": "What to do, and how to tell it worked.",
}


def render_memory_md(data):
    lines = [
        "# Memory index",
        "",
        "Generated by `python -m mem index` at %s. Do not hand-edit; edit the"
        " records and rebuild." % data.get("generated", "?"),
        "",
        "%d records: %s" % (
            data.get("count", 0),
            ", ".join("%s %s" % (v, k) for k, v in
                      sorted(data.get("counts_by_layer", {}).items())) or "none",
        ),
        "",
    ]
    for layer in schema.LAYERS:
        rows = [e for e in data["records"] if e["layer"] == layer]
        lines.append("## %s (%d)" % (layer, len(rows)))
        lines.append("")
        lines.append("_%s_" % _LAYER_BLURB[layer])
        lines.append("")
        if not rows:
            lines += ["- _(empty)_", ""]
            continue
        key = "occurred" if layer == "episodic" else "updated"
        rows.sort(key=lambda e: (e.get(key) or "", e["id"]), reverse=(layer == "episodic"))
        for entry in rows:
            hook = entry["summary"] or ", ".join(entry["tags"]) or entry["layer"]
            flag = "" if entry["status"] == "active" else " `%s`" % entry["status"]
            lines.append("- [%s](%s) - %s%s" % (entry["title"], entry["path"], hook, flag))
        lines.append("")
    return "\n".join(lines)


def main_path(root=None):  # pragma: no cover - convenience for scripts
    return Path(Store(root).index_dir) / INDEX_FILE
