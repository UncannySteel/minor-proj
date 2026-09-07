"""Populate a store with a worked example: nine records, three layers.

The scenario is one recurring problem (a flaky deploy hook) observed across
several episodes, the durable fact those episodes support, and the procedure
that fell out of them - so recall, link-spreading and consolidation all have
something real to chew on.

    python examples/seed_memories.py --root examples/store
    python -m mem --root examples/store recall "deploy hook failing" --explain
    python -m mem --root examples/store consolidate
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mem import Store, index, schema  # noqa: E402

NOW = dt.datetime.now(dt.timezone.utc)


def ago(days):
    return NOW - dt.timedelta(days=days)


EPISODES = [
    (12, "Deploy hook failed on a CRLF line ending", "failure", 0.7,
     ["deploy", "windows", "git-hooks"],
     """## What happened

The pre-push hook exited 1 with `bad interpreter`. The file had CRLF line
endings after an editor round-trip, so the shebang was `#!/bin/sh\\r`.

## Signals

- `git config core.autocrlf` was `true`
- `file .git/hooks/pre-push` reported "CRLF line terminators"

## Why it matters

Every hook failure on this machine so far has been line endings, not logic.
"""),
    (30, "Deploy hook failed again after cloning fresh", "failure", 0.6,
     ["deploy", "windows", "git-hooks"],
     """## What happened

Fresh clone, same `bad interpreter` failure on the first push. Reapplying
`dos2unix` to the hook fixed it in under a minute.

## Signals

- Failure appeared immediately after clone, before any edit
- Nothing about the hook body had changed

## Why it matters

The failure follows the checkout, so it is a configuration property of the
machine rather than of any one repository.
"""),
    (44, "dos2unix on the hook fixed the push", "success", 0.6,
     ["deploy", "windows", "git-hooks"],
     """## What happened

Ran `dos2unix .git/hooks/pre-push` and pushed again. The hook ran clean on
the first try.

## Signals

- Exit code 0, hook output as expected

## Why it matters

Confirms the fix is one command, not a rewrite.
"""),
    (5, "User asked for shorter status updates", "neutral", 0.8,
     ["communication", "preferences"],
     """## What happened

Mid-task, the user asked to skip the play-by-play and report only when a step
finished or a decision was needed.

## Signals

- Exact words: "just tell me when something lands"

## Why it matters

Applies to every future task, not only this one.
"""),
    (3, "Long tool preamble drew a correction", "failure", 0.7,
     ["communication", "preferences"],
     """## What happened

Narrated three planned tool calls before running them; the user cut in and
asked to just run them.

## Signals

- Interruption arrived before the first tool result

## Why it matters

Second correction on the same axis in a week.
"""),
]

SEMANTIC = [
    ("se-git-hooks-need-lf",
     "Git hooks on this machine need LF line endings", "constraint", 0.95,
     ["deploy", "windows", "git-hooks"],
     ["ep-deploy-1", "ep-deploy-2", "ep-deploy-3"],
     """## Claim

`core.autocrlf=true` on this Windows machine rewrites shell hooks to CRLF,
which breaks the shebang. Hooks must be stored and checked out with LF.

## Scope

Holds while `core.autocrlf` stays `true` and hooks are `#!/bin/sh` scripts.
Retire it if the repo gains a `.gitattributes` pinning hook files to LF.

## Evidence

- [[ep-deploy-1]] - first observation, CRLF confirmed by `file`
- [[ep-deploy-2]] - recurred on a clean clone, so it is machine-level
- [[ep-deploy-3]] - `dos2unix` resolved it
"""),
    ("se-terse-progress-reports",
     "User wants terse, outcome-only progress reports", "preference", 0.85,
     ["communication", "preferences"],
     ["ep-comms-1", "ep-comms-2"],
     """## Claim

Report when a step lands or a decision is needed. No narration of planned
tool calls, no per-step commentary.

## Scope

All tasks with this user until they ask for more detail.

## Evidence

- [[ep-comms-1]] - stated directly
- [[ep-comms-2]] - enforced by interruption when ignored
"""),
]

PROCEDURAL = [
    ("pr-fix-windows-git-hook",
     "Fix a failing git hook on Windows", 0.9, "active", 4, 4, 0,
     ["deploy", "windows", "git-hooks"],
     ["se-git-hooks-need-lf", "ep-deploy-3"],
     "A git hook exits non-zero with 'bad interpreter' or fails right after a clone",
     """## Trigger

A git hook fails with `bad interpreter`, or any hook fails on a fresh clone
before the hook body has been touched.

## Steps

1. `file .git/hooks/<hook>` - confirm "CRLF line terminators".
2. `dos2unix .git/hooks/<hook>` (or rewrite with LF endings).
3. Re-run the operation that fired the hook.
4. If it recurs across clones, add `*.sh text eol=lf` to `.gitattributes`.

## Verification

The hook runs to completion and the push or commit succeeds on the first try.

## Failure modes

- Still failing after dos2unix -> the shebang path itself is wrong; check
  `which sh`.
- Fixed but returns next clone -> step 4 was skipped.
"""),
    ("pr-terse-progress-reports",
     "Report progress the way this user asked", 0.8, "active", 3, 3, 0,
     ["communication", "preferences"],
     ["se-terse-progress-reports"],
     "Any multi-step task where progress could be narrated",
     """## Trigger

Any task long enough to tempt a running commentary.

## Steps

1. Do the work; batch independent tool calls.
2. Speak when a step lands or a decision needs the user.
3. Keep the closing summary to what changed and what is left.

## Verification

No mid-task interruption asking you to get on with it.

## Failure modes

- User interrupts to redirect -> you narrated; drop back to outcomes only.
"""),
]


def seed(root):
    store = Store(root)
    store.wipe()
    ids = {}

    ep_ids = ["ep-deploy-1", "ep-deploy-2", "ep-deploy-3", "ep-comms-1", "ep-comms-2"]
    for (days, title, outcome, salience, tags, body), rec_id in zip(EPISODES, ep_ids):
        when = ago(days)
        record = store.create("episodic", title, body=body, when=when,
                              id=rec_id, occurred=schema.now_iso(when),
                              outcome=outcome, salience=salience, tags=tags,
                              source="observed", session="seed")
        ids[record.id] = record

    for rec_id, title, kind, confidence, tags, evidence, body in SEMANTIC:
        record = store.create("semantic", title, body=body, id=rec_id, kind=kind,
                              confidence=confidence, salience=0.8, tags=tags,
                              evidence=evidence, source="derived")
        ids[record.id] = record

    for (rec_id, title, confidence, status, runs, ok, bad, tags, links, trigger, body) in PROCEDURAL:
        record = store.create("procedural", title, body=body, id=rec_id, trigger=trigger,
                              confidence=confidence, status=status, runs=runs,
                              successes=ok, failures=bad, salience=0.7,
                              tags=tags, links=links, derived_from=links[:1],
                              source="derived")
        ids[record.id] = record

    data = index.save(store)
    return store, data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent / "store"))
    args = parser.parse_args(argv)
    store, data = seed(args.root)
    print("seeded %d records into %s" % (data["count"], store.root))
    for layer, count in sorted(data["counts_by_layer"].items()):
        print("  %-11s %d" % (layer, count))
    print("\nTry:")
    print("  python -m mem --root %s recall \"deploy hook failing\" --explain" % args.root)
    print("  python -m mem --root %s recall \"how should I report progress\" --balanced" % args.root)
    print("  python -m mem --root %s consolidate" % args.root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
