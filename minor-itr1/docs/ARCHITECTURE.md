# Architecture

## The problem with one-tier memory

A flat pile of notes conflates three different things that behave differently
over time:

- **An event** is true forever but relevant briefly. "The deploy failed on
  Tuesday" never stops being true, and stops mattering in a fortnight.
- **A fact** is relevant forever but true conditionally. "Hooks need LF
  endings" matters every time, until someone adds a `.gitattributes` and it
  quietly stops holding.
- **A habit** is neither. "When a hook fails, run `dos2unix` first" is not a
  claim about the world; it is a policy that either works or doesn't, and the
  only honest measure of it is a success rate.

Store all three the same way and you get the failure modes of single-tier
memory: old events crowd out durable facts, corrections never accumulate into
behaviour, and nothing ever gets forgotten because nothing is marked
forgettable.

## Three layers

```
                    write path                    read path
                    ----------                    ---------
  something
  happens  ──────>  EPISODIC  ─────┐               query
                    (append-only,  │                 │
                     decays)       │                 ▼
                                   │          ┌─ working set ─┐
                    consolidate    │          │  ~1 procedure  │
                        │          │          │  ~2 facts      │
                        ▼          │          │  ~2 episodes   │
  a pattern  ──────> SEMANTIC  <───┤          └───────┬───────┘
  repeats            (revised,     │                  │
                      superseded)  │                  ▼
                        │          │            act on it
                        ▼          │                  │
  a pattern  ──────> PROCEDURAL <──┘                  │
  works              (reinforced by ◄─────────────────┘
                      outcome)        reinforce: it worked / it didn't
```

### Episodic — what happened

Append-only, timestamped, cheap to write. An episode is a specific thing that
occurred once: an error, a correction, a decision, a surprise. Episodes are
the only layer that is *observed* rather than *concluded*, which makes them
the evidence base for everything above them.

They decay. Recall discounts them on a 45-day half-life, and consolidation
proposes archiving old, low-salience episodes nothing cites. This is a
feature: an episode that never became a fact or a habit and that nothing
refers back to has, by definition, taught nothing.

### Semantic — what is true

Distilled, revisable, deduplicated. One claim per record, stated in the
present tense, with an explicit **scope** — the condition under which it stops
holding — and **evidence** pointing at the episodes that support it.

Semantic records are not written from nowhere. A semantic record with no
evidence is an assertion, and the validator says so. The `supersedes` field
carries the audit trail when a claim is replaced rather than edited.

### Procedural — what to do

Trigger, steps, verification, failure modes. A procedure is a conditional
policy, and unlike a fact its truth is *measured*: `mem reinforce <id>
success|failure` increments the counters and recomputes confidence from the
observed success rate. A new procedure starts as `draft` and is promoted to
`active` after two successes — it earns trust rather than being granted it.

The verification section is not optional decoration. A procedure without an
observable success criterion cannot be reinforced, which means it can never
be shown to be wrong.

## How the layers interact

**Upward (consolidation).** Episodes accumulate; when three or more share a
tag and nothing durable cites them, `mem consolidate` proposes a semantic
promotion. When three or more *successful* episodes share a tag, it proposes
a procedural one. It never writes: naming a pattern is a judgement, and the
tool's job is to make sure the judgement is offered, not to make it.

**Downward (grounding).** Every durable record links back to the episodes it
came from. That is what makes a claim auditable — you can always ask "what
made me believe this?" and get file paths rather than a shrug.

**Sideways (activation).** Recall spreads a fraction of each hit's score to
the records it links to, so retrieving a procedure also surfaces the fact it
depends on and the episode that produced it. Retrieval follows the structure
instead of only the words.

## Retrieval, and why it is budgeted

Ranking is a weighted sum of six named components — lexical match, tag match,
salience, confidence, recency, reliability — with per-layer weights, so every
result explains itself under `--explain`. The weights encode what each layer
should be trusted for: episodes are discounted by age, facts are multiplied by
confidence, procedures by how often they have actually worked.

A relevance gate keeps salience and confidence honest: they break ties between
records that matched, and can never turn a non-match into a match.

`working_set` then imposes a shape on the result — roughly one procedure, two
facts, two episodes — instead of returning the flat top-N. A flat top-N on a
mature store returns five episodes about the same incident. The shape is the
point: to act well you want the rule to follow, the facts it rests on, and
just enough grounding to notice if this case is different.

## Forgetting

Nothing is deleted. `mem archive` moves a record to `memory/_archive/` with a
timestamp and a reason, where it stops being recalled but stays auditable, and
`mem restore` reverses it. Consolidation nominates candidates; a human or the
agent decides. Deletion is irreversible and memory is the wrong place to be
irreversible.

## Design constraints

- **Plain Markdown, one record per file.** Hand-editable, greppable,
  diffable. The tooling is an accelerator, never the only way in.
- **Standard library only.** No install step, nothing to break in six months.
- **The index is derived.** `index/` can be deleted and rebuilt from the
  records at any time; it is a cache, never the source of truth.
- **The tool proposes, the agent decides.** Every operation that requires
  judgement — promotion, merge, forgetting — produces a proposal with named
  evidence, not a write.
