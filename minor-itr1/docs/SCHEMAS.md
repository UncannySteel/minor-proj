# Record schemas

Every record is a Markdown file with a `---` fenced header. The header is a
deliberately small YAML subset: flat keys, scalars, and lists. No nesting.

`python -m mem validate --strict` checks every rule below. **Errors** mean the
record is malformed. **Warnings** mean it is legal but weak — usually that it
is missing the thing that would make it trustworthy later.

## Shared fields

| Field | Type | Notes |
|---|---|---|
| `id` | string | `ep-` / `se-` / `pr-` + slug. The prefix must match the layer. |
| `layer` | enum | `episodic`, `semantic`, `procedural` |
| `title` | string | One line. Carries triple weight in retrieval — write it like a search query you'd type in six months. |
| `created` | ISO-8601 | Set once, never edited. |
| `tags` | list | Lowercase. Tags are what consolidation clusters on, so reuse them rather than inventing near-synonyms. |
| `links` | list | Record ids. Untyped cross-references. |
| `salience` | 0.0–1.0 | How much this should matter when it matches. Defaults to 0.5; reserve >0.8 for things you'd be embarrassed to forget. |
| `confidence` | 0.0–1.0 | How sure you are. Episodes are near-1.0 (you saw it); facts and procedures earn theirs. |
| `source` | enum | `user`, `observed`, `derived`, `imported` |
| `status` | enum | `draft`, `active`, `deprecated`, `superseded`, `archived` |

Ids are addresses. `se-git-hooks-need-lf` is meant to be quotable in prose and
typable from memory; episodic ids carry a date (`ep-20260304-hook-broke`)
because episodes collide by nature and durable records should not.

## Episodic

Required: `id`, `layer`, `title`, `created`, `occurred`, `outcome`.

| Field | Type | Notes |
|---|---|---|
| `occurred` | ISO-8601 | When it happened, which is not always when you wrote it. Drives recency decay and the `YYYY-MM` file bucket. |
| `outcome` | enum | `success`, `failure`, `mixed`, `neutral`, `open` |
| `session` | string | Session or task id, for grouping. |
| `actors` | list | Who was involved. |

Body sections: `## What happened` (required), `## Signals`, `## Why it matters`.

`outcome: success` is load-bearing — it is what lets consolidation tell a
repeated *problem* (semantic) from a repeated *solution* (procedural).

```markdown
---
id: ep-20260826-deploy-hook-crlf
layer: episodic
title: Deploy hook failed on a CRLF line ending
created: 2026-08-26T09:14:00Z
occurred: 2026-08-26T09:02:00Z
outcome: failure
tags:
  - deploy
  - git-hooks
salience: 0.7
confidence: 0.9
source: observed
status: active
---

## What happened

The pre-push hook exited 1 with `bad interpreter`...
```

## Semantic

Required: `id`, `layer`, `title`, `created`, `kind`, `confidence`.

| Field | Type | Notes |
|---|---|---|
| `kind` | enum | `fact`, `entity`, `preference`, `constraint`, `project`, `reference`, `definition` |
| `subject` | string | The entity this is about, when there is one. |
| `evidence` | list | Episode ids. Empty is legal but warns. |
| `supersedes` | list | Ids this replaces. Set `status: superseded` on the old record rather than deleting it. |
| `updated` | ISO-8601 | Bumped on every revision. |

Body sections: `## Claim` (required), `## Scope`, `## Evidence`.

`## Scope` is the section people skip and then regret. A claim without a
retirement condition can only be discovered to be wrong by being wrong.

## Procedural

Required: `id`, `layer`, `title`, `created`, `trigger`, `status`.

| Field | Type | Notes |
|---|---|---|
| `trigger` | string | The situation that fires this. Written as a condition, not a topic. |
| `preconditions` | list | What must hold before step 1. |
| `derived_from` | list | The episodes or facts that produced it. |
| `uses` | list | Other procedures this composes. |
| `runs` / `successes` / `failures` | int | Maintained by `mem reinforce`. |

Body sections: `## Steps` and `## Verification` (both required),
`## Trigger`, `## Failure modes`.

Confidence is not hand-set after the first run: `mem reinforce <id>
success|failure` recomputes it as a damped success rate
(`0.3 × 0.6 + 0.7 × successes/total`), and promotes `draft` to `active` at two
successes. A procedure that has never run sits at reliability 0.5 in
retrieval — untested, not condemned.

## Front matter limitations

The parser is ~150 lines and handles what these schemas need:

- Flat keys only. `metadata:\n  type: x` parses as a `type` key at the top
  level, which is what the migration path relies on, but nested mappings are
  not a supported shape to *write*.
- Inline (`[a, b]`) and block (`- a`) lists both work.
- Strings containing both `"` and `'` do not round-trip exactly.
- No multi-line scalars, anchors, or comments-with-meaning.

If a header needs more than this, the record is trying to be a database row.
Put the complexity in the body.
