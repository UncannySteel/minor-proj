"""Recall: turn a query into a ranked, budgeted set of memories.

The score is a weighted sum of six named components, so every result can
explain itself. Weights differ per layer because the layers earn trust
differently:

    episodic    lexical match, discounted by age
    semantic    lexical match, multiplied by how sure we are
    procedural  lexical match, multiplied by how often it has worked

A second pass spreads a fraction of each hit's activation to the records it
links to, so pulling a procedure also surfaces the episode that produced it.
"""
from __future__ import annotations

import datetime as dt
import math
from collections import Counter

from . import index as index_mod
from . import schema

# Per-layer component weights. Rows sum to 1.0.
WEIGHTS = {
    "episodic": {"lex": 0.50, "tag": 0.15, "salience": 0.10,
                 "confidence": 0.05, "recency": 0.20, "reliability": 0.00},
    "semantic": {"lex": 0.55, "tag": 0.15, "salience": 0.10,
                 "confidence": 0.20, "recency": 0.00, "reliability": 0.00},
    "procedural": {"lex": 0.45, "tag": 0.15, "salience": 0.05,
                   "confidence": 0.15, "recency": 0.00, "reliability": 0.20},
}

# Durable layers answer "what do I know"; episodes answer "when did I learn it".
LAYER_PRIOR = {"semantic": 1.00, "procedural": 1.00, "episodic": 0.92}

HALF_LIFE_DAYS = 45.0   # episodic recency half-life
SPREAD = 0.18           # fraction of a neighbour's score that leaks across a link
STATUS_PENALTY = {"active": 1.0, "draft": 0.85, "deprecated": 0.35,
                  "superseded": 0.25, "archived": 0.2}
BM25_K1, BM25_B = 1.2, 0.75


class Hit:
    __slots__ = ("id", "layer", "title", "path", "score", "parts", "snippet",
                 "tags", "via")

    def __init__(self, entry, score, parts, snippet, via=None):
        self.id = entry["id"]
        self.layer = entry["layer"]
        self.title = entry["title"]
        self.path = entry["path"]
        self.tags = entry["tags"]
        self.score = score
        self.parts = parts
        self.snippet = snippet
        self.via = via

    def as_dict(self):
        return {"id": self.id, "layer": self.layer, "title": self.title,
                "path": self.path, "score": round(self.score, 4),
                "tags": self.tags, "snippet": self.snippet, "via": self.via,
                "parts": {k: round(v, 4) for k, v in self.parts.items()}}

    def __repr__(self):  # pragma: no cover - debugging aid
        return "<Hit %.3f %s>" % (self.score, self.id)


def _recency(entry, now):
    stamp = schema.parse_ts(entry.get("occurred") or entry.get("created"))
    if stamp is None:
        return 0.5
    age_days = max(0.0, (now - stamp).total_seconds() / 86400.0)
    return 0.5 ** (age_days / HALF_LIFE_DAYS)


def _reliability(entry):
    ok, bad = entry.get("successes", 0), entry.get("failures", 0)
    if ok + bad == 0:
        return 0.5  # untested procedures start agnostic, not condemned
    return ok / float(ok + bad)


def _bm25(entry, query_terms, df, n_docs, avg_len):
    score, length = 0.0, max(1, entry.get("length", 1))
    terms = entry.get("terms", {})
    for term, q_count in query_terms.items():
        tf = terms.get(term, 0)
        if not tf:
            continue
        idf = math.log(1 + (n_docs - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5))
        denom = tf + BM25_K1 * (1 - BM25_B + BM25_B * length / avg_len)
        score += q_count * idf * (tf * (BM25_K1 + 1)) / denom
    return score


def search(store, query, k=8, layers=None, now=None, data=None,
           include_archived=False, min_score=0.02, spread=SPREAD):
    """Rank records against ``query``. Returns a list of :class:`Hit`."""
    data = data or index_mod.load(store)
    entries = [e for e in data["records"]
               if (layers is None or e["layer"] in layers)
               and (include_archived or e.get("status") != "archived")]
    if not entries:
        return []

    now = now or dt.datetime.now(dt.timezone.utc)
    query_terms = Counter(index_mod.tokenize(query))
    query_set = set(query_terms)
    df, n_docs = data.get("df", {}), max(1, data.get("count", len(entries)))
    avg_len = data.get("avg_length") or 1.0

    base, by_id = {}, {}
    for entry in entries:
        by_id[entry["id"]] = entry
        raw_lex = _bm25(entry, query_terms, df, n_docs, avg_len)
        parts = {
            "lex": raw_lex / (raw_lex + 3.0),          # squash into [0,1)
            "tag": (len(query_set & set(entry["tags"])) / len(query_set)) if query_set else 0.0,
            "salience": entry.get("salience", 0.5),
            "confidence": entry.get("confidence", 0.5),
            "recency": _recency(entry, now),
            "reliability": _reliability(entry),
        }
        weights = WEIGHTS[entry["layer"]]
        score = sum(weights[name] * value for name, value in parts.items())
        score *= LAYER_PRIOR.get(entry["layer"], 1.0)
        score *= STATUS_PENALTY.get(entry.get("status", "active"), 1.0)
        # Relevance gate: salience and confidence break ties between matches,
        # they never make a non-match into one. Zero here means the record can
        # still surface, but only by being linked to something that did match.
        if parts["lex"] <= 0.0 and parts["tag"] <= 0.0:
            score = 0.0
        base[entry["id"]] = score
        entry["_parts"] = parts

    # Spreading activation: one hop, both directions, best neighbour only.
    neighbours = {rid: set() for rid in base}
    for entry in entries:
        for link in entry.get("links", []):
            if link in neighbours:
                neighbours[entry["id"]].add(link)
                neighbours[link].add(entry["id"])

    final, via = {}, {}
    for rid, score in base.items():
        best, source = 0.0, None
        for neighbour in neighbours[rid]:
            if base.get(neighbour, 0.0) > best:
                best, source = base[neighbour], neighbour
        boost = spread * best
        final[rid] = score + boost
        if boost > score and source:
            via[rid] = source

    hits = []
    for rid, score in final.items():
        if score < min_score:
            continue
        entry = by_id[rid]
        hits.append(Hit(entry, score, entry.pop("_parts", {}),
                        snippet(entry, query_set), via.get(rid)))
    hits.sort(key=lambda h: (-h.score, h.id))
    return hits[:k]


def snippet(entry, query_set, limit=200):
    """Prefer a line that actually contains a query term."""
    text = entry.get("summary") or ""
    if not query_set:
        return text
    for term in query_set:
        if term in text.lower():
            return text
    return text[:limit]


def working_set(store, query, budget=6, now=None, data=None):
    """A balanced context slice: never all-episodic, never all-semantic.

    Recall for a task usually wants one procedure to follow, the facts it
    depends on, and a couple of episodes for grounding. Enforcing that shape
    beats taking the top-N of a single ranking.
    """
    quotas = {"procedural": max(1, budget // 3),
              "semantic": max(1, budget // 3),
              "episodic": max(1, budget - 2 * (budget // 3))}
    data = data or index_mod.load(store)
    picked, seen = [], set()
    for layer, quota in quotas.items():
        for hit in search(store, query, k=quota, layers=(layer,), now=now, data=data):
            if hit.id not in seen:
                seen.add(hit.id)
                picked.append(hit)
    # Backfill any unused quota from the open ranking.
    if len(picked) < budget:
        for hit in search(store, query, k=budget * 2, now=now, data=data):
            if hit.id not in seen:
                seen.add(hit.id)
                picked.append(hit)
            if len(picked) >= budget:
                break
    picked.sort(key=lambda h: (-h.score, h.id))
    return picked[:budget]


def render(hits, explain=False):
    """Plain-text rendering used by the CLI and safe to paste into context."""
    if not hits:
        return "(no memories matched)"
    lines = []
    for i, hit in enumerate(hits, 1):
        head = "%2d. [%.3f] %-10s %s" % (i, hit.score, hit.layer, hit.title)
        lines.append(head)
        lines.append("      id: %s  path: %s" % (hit.id, hit.path))
        if hit.tags:
            lines.append("      tags: %s" % ", ".join(hit.tags))
        if hit.snippet:
            lines.append("      %s" % hit.snippet)
        if hit.via:
            lines.append("      (surfaced via link from %s)" % hit.via)
        if explain:
            lines.append("      parts: %s" % ", ".join(
                "%s=%.2f" % (k, v) for k, v in sorted(hit.parts.items())))
    return "\n".join(lines)
