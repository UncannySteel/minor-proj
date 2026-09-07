# Migration from flat memory

The existing convention is one fact per file, typed `user`, `feedback`,
`project` or `reference`, with a `MEMORY.md` index. That maps onto the layers
without loss:

| Flat `type` | Target | Why |
|---|---|---|
| `user` | `semantic` / `preference` | Who the person is and what they want — durable claims. |
| `reference` | `semantic` / `reference` | A pointer that stays true. |
| `project` | `semantic` / `project` | State of ongoing work; revise rather than re-add. |
| `feedback` | `procedural` (`draft`) | **The interesting case.** |
| anything else | `semantic` / `fact` | Conservative default. |

## Why feedback becomes procedural

Flat feedback records already have the shape of a procedure — they carry a
**Why** and a **How to apply** — they just have nowhere to put a trigger or a
verification, and no way to record whether following them actually worked.

Moving them into the procedural layer gains three things the flat store cannot
express: a trigger that says *when* the guidance applies, a verification that
makes it falsifiable, and run counters so guidance that stops fitting decays
on evidence instead of on someone's memory of a conversation.

Imported procedures land as `status: draft` with `confidence: 0.6`. They have
not been observed working *in this system* yet, and the reinforcement loop is
how they earn their status back. Two successful runs promotes to `active`.

## Running it

Dry run first — it reads the source and writes nothing:

```bash
python -m mem migrate "C:/Users/<you>/<agent-config-dir>/projects/<project>/memory"
```

Then apply into a scratch root and inspect before committing to it:

```bash
python -m mem --root ./examples/store-migrated migrate "<source>" --apply
python -m mem --root ./examples/store-migrated validate --strict
```

The source directory is never modified. `MEMORY.md`, `README.md` and
`index.md` are skipped — the index is regenerated, not imported.

## What the reshape does, and doesn't

The original prose is preserved **verbatim** under the target layer's
headings. Fields the new schema wants but the old file never had become
explicit `<TODO>` placeholders rather than inventions:

```markdown
## Trigger

<the flat record's `description`, or TODO>

## Steps

<the original body, unchanged>

## Verification

<TODO: what observable says this was followed?>
```

Those TODOs are the actual migration work, and they are deliberately visible.
Filling in a verification requires deciding what would count as following the
guidance — which is exactly the thinking the flat format let you skip.

## Afterwards

1. `python -m mem validate --strict` — the warnings list every missing
   section and every unevidenced claim.
2. Fill the TODOs on the procedures you actually use. Leave the rest; they'll
   surface the next time they're recalled.
3. `python -m mem consolidate` — imported records have no evidence links, so
   expect merge candidates where the flat store held two notes on one topic.
4. Backfill evidence opportunistically. When an imported claim proves itself
   in a session, write that session's episode and add it to `evidence:`. The
   store gets grounded through use rather than through a migration sprint.

Both stores can run side by side during the transition; nothing here writes
outside its own root.
