# minor-itr1 — layered agent memory

A working framework for memory in three layers, on plain Markdown files, with
no dependencies beyond the Python standard library.

| Layer | Question | Behaviour |
|---|---|---|
| **episodic** | What happened? | Append-only, timestamped, decays with age |
| **semantic** | What is true? | Revised and superseded, cites its evidence |
| **procedural** | What do I do? | Scored by outcome — earns confidence, or loses it |

The point of separating them is that they age differently. An event is true
forever and relevant briefly; a fact is relevant forever and true
conditionally; a habit is neither, and the only honest measure of it is
whether it keeps working. One tier cannot serve all three, which is why flat
memory drifts into a pile where nothing is ever promoted or forgotten.

## Quickstart

```bash
cd minor-itr1
python examples/seed_memories.py --root examples/store
python -m mem --root examples/store recall "deploy hook failing" --explain
python -m mem --root examples/store recall "how should I report progress" --balanced
python -m mem --root examples/store consolidate
```

Then start your own store:

```bash
python -m mem init
python -m mem new episodic "Deploy hook failed on a CRLF line ending" \
  --tag deploy --tag git-hooks --set outcome=failure --set salience=0.7
python -m mem recall "deploy hook" --balanced
```

`--root` selects the store; without it, `MEM_ROOT` or this directory is used.

## What recall looks like

```
 1. [0.783] procedural Fix a failing git hook on Windows
      id: pr-fix-windows-git-hook  path: memory/procedural/pr-fix-windows-git-hook.md
      tags: deploy, windows, git-hooks
      parts: confidence=0.90, lex=0.61, recency=1.00, reliability=1.00, salience=0.70, tag=0.33
 2. [0.612] semantic   Git hooks on this machine need LF line endings
 3. [0.583] episodic   Deploy hook failed on a CRLF line ending
```

The procedure ranks first because it has run four times without failing; the
fact ranks above the episodes because it is what you actually need to act. Six
named score components, per-layer weights, and `--explain` to see them — every
result can justify itself.

`--balanced` returns a shaped working set (about one procedure, two facts, two
episodes) rather than a flat top-N, which on a mature store is five episodes
about the same incident.

## Commands

| Command | Does |
|---|---|
| `init` | Create the layout |
| `new <layer> <title>` | Write a record (`--tag`, `--link`, `--set k=v`, `--body -`) |
| `recall <query>` | Rank records (`--balanced`, `--explain`, `--layer`, `--json`) |
| `show <id>` | Print one record |
| `index` | Rebuild `index/index.json` and `index/MEMORY.md` |
| `validate [--strict]` | Check every record against its schema |
| `consolidate` | Propose promotions, merges, contradictions, forgetting |
| `reinforce <id> success\|failure` | Score a procedure; updates confidence and status |
| `archive <id>` / `restore <id>` | Forget reversibly |
| `stats` | Store health |
| `errors [--stats\|--tail N\|--verbose\|--clear]` | Read the structured error log |
| `migrate <dir> [--apply]` | Import a flat memory directory into the layers |

## Layout

```
minor-itr1/
  mem/                    the framework (stdlib only, ~2000 lines)
    frontmatter.py        minimal YAML-subset parser
    schema.py             field contracts and validation per layer
    store.py              file-backed records: create, get, archive, restore
    index.py              index.json for retrieval, MEMORY.md for humans
    recall.py             scoring, spreading activation, working sets
    consolidate.py        promotion, merge, contradiction and decay detectors
    errorlog.py           append-only JSONL error log, grouped by fingerprint
    migrate.py            flat -> layered import
    cli.py                python -m mem
  memory/
    episodic/YYYY-MM/     bucketed, because episodes pile up
    semantic/             flat, because ids are addresses
    procedural/           flat, same reason
    _archive/             forgotten, not deleted
  index/                  derived; safe to delete and rebuild
  logs/errors.jsonl       structured error log; derived, safe to delete
  docs/                   architecture, schemas, protocols, operating manual
  templates/              one per layer, for writing records by hand
  examples/               a nine-record worked scenario
  tests/                  80 tests, stdlib unittest
```

## Docs

- [Architecture](docs/ARCHITECTURE.md) — why three layers, how they interact,
  how retrieval and forgetting work
- [Schemas](docs/SCHEMAS.md) — every field, every validation rule
- [Protocols](docs/PROTOCOLS.md) — the encode / consolidate / recall /
  reinforce loops, and the anti-patterns
- [Operating manual](docs/OPERATING_MANUAL.md) — agent-facing decision
  procedure: which layer, when to write, how to handle contradictions
- [Migration](docs/MIGRATION.md) — importing a flat `user`/`feedback`/
  `project`/`reference` store
- [Code cleanup review](docs/CODE_CLEANUP_REVIEW.md) — a read-and-report-only
  maintainability audit sheet to point an agent at. Produces a report, never a
  diff.

## Error logging

Failures append to `logs/errors.jsonl` as one JSON object per line, with a
`fingerprint` that strips instance noise (paths, numbers, hex) so recurrences
of the same *shape* group together.

```bash
python -m mem errors --tail 5 --verbose
python -m mem errors --stats          # counts, plus failures seen 3+ times
```

It is deliberately **not** the episodic layer. An exception is a machine fact:
noisy, high-volume, mostly uninteresting. An episode is a considered note
about something that taught you something. `--stats` is the bridge — a failure
shape that keeps recurring is the one worth writing an episode about by hand.

Unhandled CLI exceptions are logged and then surfaced, never swallowed; the
same goes for records the store cannot read during a walk.

## Design commitments

- **Plain Markdown, one record per file.** Greppable, diffable,
  hand-editable. The tooling is an accelerator, never the only way in.
- **Standard library only.** No install step, nothing to rot.
- **The index is derived.** Delete `index/` and rebuild from the records; it
  is a cache, never the source of truth.
- **The tool proposes, the agent decides.** Promotion, merging and forgetting
  are judgements. Every one produces a proposal with named evidence, not a
  silent write.
- **Forgetting is a move.** `archive` is reversible and stamped with a reason.

## Tests

```bash
python -m unittest discover -s tests -t .
```

## Status

Iteration 1. The retrieval weights, the 45-day episodic half-life and the
`min_support=3` promotion threshold are defensible defaults, not tuned
constants — they live at the top of `recall.py` and `consolidate.py` and are
meant to be moved once a real store has enough records to argue with them.
