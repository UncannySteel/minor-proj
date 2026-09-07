"""Consolidation: the pass that turns episodes into knowledge and habits.

This module deliberately *proposes* rather than writes. Deciding that three
episodes mean one durable fact is a judgement call - the tool finds the
candidates and does the bookkeeping; the agent writes the sentence. Every
proposal names its evidence so the promotion can be checked or rejected.

Detectors:

    promote_semantic     a tag recurs across episodes with no semantic record
    promote_procedural   a tag recurs across *successful* episodes
    merge_semantic       two durable records say nearly the same thing
    contradiction        near-duplicate subjects with opposing confidence
    decay                old, low-salience episodes nothing else cites
    hygiene              dangling links, schema errors, orphans
"""
from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict

from . import index as index_mod
from . import schema

MIN_SUPPORT = 3           # episodes needed before a pattern counts
DECAY_AGE_DAYS = 120.0    # older than this and unloved -> archive candidate
DECAY_SALIENCE = 0.4
STALE_SEMANTIC_DAYS = 365.0
MERGE_THRESHOLD = 0.6     # Jaccard over title+summary tokens


def _tokens(entry):
    return set(index_mod.tokenize(entry["title"] + " " + (entry.get("summary") or "")))


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def analyze(store, data=None, now=None, min_support=MIN_SUPPORT):
    """Return a dict of proposal lists. Pure analysis - writes nothing."""
    data = data or index_mod.load(store)
    now = now or dt.datetime.now(dt.timezone.utc)
    records = [e for e in data["records"] if e.get("status") != "archived"]
    by_id = {e["id"]: e for e in records}
    by_layer = defaultdict(list)
    for entry in records:
        by_layer[entry["layer"]].append(entry)

    # Which episodes have already been consumed by a durable record?
    consumed = set()
    for entry in by_layer["semantic"] + by_layer["procedural"]:
        consumed.update(entry.get("links", []))

    report = {
        "generated": schema.now_iso(now),
        "totals": dict(Counter(e["layer"] for e in records)),
        "promote_semantic": [],
        "promote_procedural": [],
        "merge_semantic": [],
        "contradictions": [],
        "decay": [],
        "hygiene": [],
    }

    # -- tag clusters over episodes ------------------------------------
    clusters = defaultdict(list)
    for entry in by_layer["episodic"]:
        for tag in entry["tags"]:
            clusters[tag].append(entry)

    durable_tags = Counter()
    for entry in by_layer["semantic"] + by_layer["procedural"]:
        durable_tags.update(entry["tags"])

    for tag, group in sorted(clusters.items()):
        fresh = [e for e in group if e["id"] not in consumed]
        if len(group) < min_support or len(fresh) < min_support - durable_tags[tag]:
            continue
        wins = [e for e in group if _outcome(by_id, e) == "success"]
        if not durable_tags[tag] or len(fresh) >= min_support:
            report["promote_semantic"].append({
                "tag": tag,
                "support": len(group),
                "uncovered": len(fresh),
                "evidence": [e["id"] for e in group],
                "suggested_id": "se-%s" % schema.slugify(tag),
                "why": "%d episodes tagged '%s'; %d not yet cited by any durable"
                       " record" % (len(group), tag, len(fresh)),
            })
        if len(wins) >= min_support:
            report["promote_procedural"].append({
                "tag": tag,
                "support": len(wins),
                "evidence": [e["id"] for e in wins],
                "suggested_id": "pr-%s" % schema.slugify(tag),
                "why": "%d episodes tagged '%s' ended in success; that is a"
                       " repeatable move, not a one-off" % (len(wins), tag),
            })

    # -- near-duplicate durable records --------------------------------
    durable = by_layer["semantic"] + by_layer["procedural"]
    token_cache = {e["id"]: _tokens(e) for e in durable}
    for i, left in enumerate(durable):
        for right in durable[i + 1:]:
            if left["layer"] != right["layer"]:
                continue
            overlap = _jaccard(token_cache[left["id"]], token_cache[right["id"]])
            if overlap < MERGE_THRESHOLD:
                continue
            gap = abs(left["confidence"] - right["confidence"])
            bucket = "contradictions" if gap >= 0.4 else "merge_semantic"
            report[bucket].append({
                "a": left["id"], "b": right["id"],
                "similarity": round(overlap, 3),
                "confidence_gap": round(gap, 3),
                "why": "%.0f%% token overlap; %s" % (
                    overlap * 100,
                    "confidences disagree - one may supersede the other"
                    if bucket == "contradictions" else "likely the same claim twice"),
            })

    # -- decay candidates ----------------------------------------------
    cited = set()
    for entry in records:
        cited.update(entry.get("links", []))
    for entry in by_layer["episodic"]:
        stamp = schema.parse_ts(entry.get("occurred") or entry.get("created"))
        if stamp is None:
            continue
        age = (now - stamp).total_seconds() / 86400.0
        if age > DECAY_AGE_DAYS and entry["salience"] < DECAY_SALIENCE \
                and entry["id"] not in cited:
            report["decay"].append({
                "id": entry["id"], "age_days": round(age),
                "salience": entry["salience"],
                "why": "%d days old, salience %.2f, cited by nothing"
                       % (round(age), entry["salience"]),
            })

    for entry in by_layer["semantic"]:
        stamp = schema.parse_ts(entry.get("updated") or entry.get("created"))
        if stamp is None:
            continue
        age = (now - stamp).total_seconds() / 86400.0
        if age > STALE_SEMANTIC_DAYS and entry["confidence"] < 0.5:
            report["decay"].append({
                "id": entry["id"], "age_days": round(age),
                "salience": entry["salience"],
                "why": "unrevised for %d days at confidence %.2f - reconfirm"
                       " or retire" % (round(age), entry["confidence"]),
            })

    # -- hygiene --------------------------------------------------------
    for record in store.records():
        errors, warnings = record.validate()
        for problem in errors:
            report["hygiene"].append({"id": record.id, "severity": "error",
                                      "detail": problem})
        for problem in warnings:
            report["hygiene"].append({"id": record.id, "severity": "warning",
                                      "detail": problem})
        for link in record.links:
            if link not in by_id and store.get(link) is None:
                report["hygiene"].append({
                    "id": record.id, "severity": "error",
                    "detail": "dangling link -> %s" % link})

    for entry in by_layer["procedural"]:
        if not entry.get("links") and not entry.get("runs"):
            report["hygiene"].append({
                "id": entry["id"], "severity": "warning",
                "detail": "procedure has neither evidence nor a run record;"
                          " it is a guess until something confirms it"})

    return report


def _outcome(by_id, entry):
    """Outcome lives in the file, not the index entry; fall back to neutral."""
    return entry.get("outcome") or "neutral"


def render(report, verbose=False):
    lines = ["# Consolidation report", "",
             "Generated %s" % report["generated"], "",
             "Store: %s" % (", ".join("%s %s" % (v, k) for k, v in
                                      sorted(report["totals"].items())) or "empty"),
             ""]

    def section(key, heading, formatter):
        rows = report.get(key) or []
        lines.append("## %s (%d)" % (heading, len(rows)))
        lines.append("")
        if not rows:
            lines.extend(["_nothing to do_", ""])
            return
        for row in (rows if verbose else rows[:15]):
            lines.append("- " + formatter(row))
        if not verbose and len(rows) > 15:
            lines.append("- _...%d more_" % (len(rows) - 15))
        lines.append("")

    section("promote_semantic", "Promote to semantic",
            lambda r: "`%s` <- %s (%s)" % (r["suggested_id"],
                                           ", ".join(r["evidence"][:5]), r["why"]))
    section("promote_procedural", "Promote to procedural",
            lambda r: "`%s` <- %s (%s)" % (r["suggested_id"],
                                           ", ".join(r["evidence"][:5]), r["why"]))
    section("merge_semantic", "Merge candidates",
            lambda r: "`%s` + `%s` - %s" % (r["a"], r["b"], r["why"]))
    section("contradictions", "Possible contradictions",
            lambda r: "`%s` vs `%s` - %s" % (r["a"], r["b"], r["why"]))
    section("decay", "Forgetting candidates",
            lambda r: "`%s` - %s" % (r["id"], r["why"]))
    section("hygiene", "Hygiene",
            lambda r: "[%s] `%s` %s" % (r["severity"], r["id"], r["detail"]))

    lines += ["## Next step", "",
              "Nothing above has been written. Read the evidence, write the"
              " promotion by hand (`python -m mem new ...`), link it back with"
              " `evidence:`, then re-run `python -m mem index`.", ""]
    return "\n".join(lines)
