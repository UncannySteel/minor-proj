"""Field contracts for the three memory layers.

Each layer answers a different question:

    episodic    what happened, once, at a time
    semantic    what is true, until superseded
    procedural  what to do, and how to tell it worked

Everything here is data plus a validator; no I/O. ``store.py`` owns the files.
"""
from __future__ import annotations

import datetime as dt
import re

LAYERS = ("episodic", "semantic", "procedural")
PREFIX = {"episodic": "ep", "semantic": "se", "procedural": "pr"}
LAYER_BY_PREFIX = {v: k for k, v in PREFIX.items()}

# Emission order. Anything not listed lands after these, alphabetically.
FIELD_ORDER = {
    "episodic": [
        "id", "layer", "title", "created", "occurred", "session", "actors",
        "outcome", "tags", "links", "salience", "confidence", "source",
        "status",
    ],
    "semantic": [
        "id", "layer", "title", "created", "updated", "kind", "subject",
        "tags", "links", "evidence", "supersedes", "salience", "confidence",
        "source", "status",
    ],
    "procedural": [
        "id", "layer", "title", "created", "updated", "trigger",
        "preconditions", "tags", "links", "derived_from", "uses", "runs",
        "successes", "failures", "salience", "confidence", "source", "status",
    ],
}

REQUIRED = {
    "episodic": ("id", "layer", "title", "created", "occurred", "outcome"),
    "semantic": ("id", "layer", "title", "created", "kind", "confidence"),
    "procedural": ("id", "layer", "title", "created", "trigger", "status"),
}

LIST_FIELDS = frozenset(
    ("tags", "links", "actors", "evidence", "supersedes", "derived_from",
     "uses", "preconditions")
)
UNIT_FIELDS = frozenset(("salience", "confidence"))
TS_FIELDS = frozenset(("created", "updated", "occurred"))

ENUMS = {
    "outcome": ("success", "failure", "mixed", "neutral", "open"),
    "kind": ("fact", "entity", "preference", "constraint", "project",
             "reference", "definition"),
    "source": ("user", "observed", "derived", "imported"),
    "status": ("draft", "active", "deprecated", "superseded", "archived"),
}
ENUM_BY_LAYER = {
    "episodic": ("outcome", "source", "status"),
    "semantic": ("kind", "source", "status"),
    "procedural": ("source", "status"),
}

# Sections a well-formed body carries. Missing ones are warnings, not errors:
# a half-written memory still beats a lost one.
BODY_SECTIONS = {
    "episodic": ("## What happened",),
    "semantic": ("## Claim",),
    "procedural": ("## Steps", "## Verification"),
}

TEMPLATES = {
    "episodic": """## What happened

<one paragraph, past tense, concrete enough to recognise again>

## Signals

- <the observable detail worth re-reading later>

## Why it matters

<one line: the hook a future recall will match on>
""",
    "semantic": """## Claim

<the durable fact, present tense, one or two sentences>

## Scope

<when this holds - and the condition that would retire it>

## Evidence

- [[ep-...]] - <what that episode showed>
""",
    "procedural": """## Trigger

<the situation that should fire this procedure>

## Steps

1. <action>
2. <action>

## Verification

<how you know it worked, stated as an observable>

## Failure modes

- <what goes wrong> -> <the recovery>
""",
}

DEFAULTS = {
    "episodic": {"outcome": "neutral", "salience": 0.5, "confidence": 0.9,
                 "source": "observed", "status": "active", "tags": [],
                 "links": [], "actors": []},
    "semantic": {"kind": "fact", "salience": 0.5, "confidence": 0.7,
                 "source": "derived", "status": "active", "tags": [],
                 "links": [], "evidence": [], "supersedes": []},
    "procedural": {"salience": 0.5, "confidence": 0.6, "source": "derived",
                   "status": "draft", "tags": [], "links": [],
                   "derived_from": [], "uses": [], "preconditions": [],
                   "runs": 0, "successes": 0, "failures": 0},
}

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")
_ID_RE = re.compile(r"^(ep|se|pr)-[a-z0-9][a-z0-9-]*$")


def now_iso(when=None):
    when = when or dt.datetime.now(dt.timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.timezone.utc)
    stamp = when.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat()
    return stamp.replace("+00:00", "Z")


def parse_ts(value):
    """Lenient ISO-8601 -> aware datetime, or None."""
    if isinstance(value, dt.datetime):
        return value if value.tzinfo else value.replace(tzinfo=dt.timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        out = dt.datetime.fromisoformat(text)
    except ValueError:
        try:
            out = dt.datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return out if out.tzinfo else out.replace(tzinfo=dt.timezone.utc)


def slugify(text, max_words=6):
    words = [w for w in _SLUG_STRIP.sub("-", str(text).lower()).split("-") if w]
    return "-".join(words[:max_words]) or "untitled"


def default_meta(layer, title, when=None):
    if layer not in LAYERS:
        raise ValueError("unknown layer: %r" % (layer,))
    stamp = now_iso(when)
    meta = {"layer": layer, "title": title, "created": stamp}
    meta.update({k: (list(v) if isinstance(v, list) else v)
                 for k, v in DEFAULTS[layer].items()})
    if layer == "episodic":
        meta["occurred"] = stamp
    else:
        meta["updated"] = stamp
    return meta


def validate(meta, body=""):
    """Return ``(errors, warnings)``; errors mean the record is malformed."""
    errors, warnings = [], []
    layer = meta.get("layer")
    if layer not in LAYERS:
        return ["layer must be one of %s, got %r" % (LAYERS, layer)], warnings

    for field in REQUIRED[layer]:
        value = meta.get(field)
        if value is None or value == "" or value == []:
            errors.append("missing required field: %s" % field)

    rec_id = meta.get("id")
    if isinstance(rec_id, str):
        if not _ID_RE.match(rec_id):
            errors.append("id %r is not <prefix>-<slug>" % rec_id)
        elif LAYER_BY_PREFIX.get(rec_id.split("-", 1)[0]) != layer:
            errors.append("id prefix of %r disagrees with layer %r" % (rec_id, layer))

    for field in ENUM_BY_LAYER[layer]:
        value = meta.get(field)
        if value is not None and value != "" and value not in ENUMS[field]:
            errors.append("%s=%r not in %s" % (field, value, ENUMS[field]))

    for field in UNIT_FIELDS:
        if field in meta and meta[field] is not None:
            value = meta[field]
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append("%s must be a number in [0,1], got %r" % (field, value))
            elif not 0.0 <= float(value) <= 1.0:
                errors.append("%s=%s outside [0,1]" % (field, value))

    for field in LIST_FIELDS & set(meta):
        if not isinstance(meta[field], list):
            errors.append("%s must be a list, got %s"
                          % (field, type(meta[field]).__name__))

    for field in TS_FIELDS & set(meta):
        if meta[field] and parse_ts(meta[field]) is None:
            errors.append("%s=%r is not an ISO-8601 timestamp" % (field, meta[field]))

    if layer == "procedural":
        runs = meta.get("runs", 0) or 0
        ok = meta.get("successes", 0) or 0
        bad = meta.get("failures", 0) or 0
        if ok + bad > runs:
            warnings.append("successes+failures (%s) exceeds runs (%s)" % (ok + bad, runs))

    for section in BODY_SECTIONS[layer]:
        if section not in (body or ""):
            warnings.append("body is missing section %r" % section)

    for link in list(meta.get("links", [])) + list(meta.get("evidence", [])):
        if isinstance(link, str) and not _ID_RE.match(link.strip("[]")):
            warnings.append("link %r does not look like a record id" % link)

    if layer == "semantic" and not meta.get("evidence"):
        warnings.append("semantic record has no evidence; it is an assertion, not a memory")

    return errors, warnings
