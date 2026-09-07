# Protocols

Four loops. Each one is short on purpose — a memory system that takes effort
to use gets used once.

---

## 1. Encode — something just happened

**When:** a correction, a surprise, a failure with a diagnosable cause, a
decision with a reason, a stated preference. Not: anything the repo already
records (code structure, git history, config), or anything that only matters
until the end of this task.

**Where:** the episodic layer, always. Even when you already know the general
lesson, write the episode first — it becomes the evidence for the claim, and
a claim with evidence survives being questioned.

```bash
python -m mem new episodic "Deploy hook failed on a CRLF line ending" \
  --tag deploy --tag git-hooks --set outcome=failure --set salience=0.7 --body -
```

**The bar for salience:** 0.5 is "worth having". Above 0.8 means you would be
visibly worse at your job for having forgotten it. Most things are 0.5.

**Tags are the consolidation surface.** Reuse an existing tag over coining a
near-synonym; `deploy` and `deployment` as two tags means a pattern that
recurred six times looks like two patterns that recurred three times.

---

## 2. Consolidate — periodically, or when a pattern is obvious

**When:** end of a substantial session, or whenever you notice you are writing
the third episode about the same thing.

```bash
python -m mem consolidate
```

The report proposes; you decide. For each promotion candidate:

1. **Read the actual episodes.** The tool clustered on a tag, which is a
   proxy. Three episodes tagged `deploy` might be three unrelated problems.
2. **Write one sentence.** If the pattern doesn't compress to a sentence with
   a scope condition, it isn't a fact yet — leave it as episodes.
3. **Cite the evidence.** Put the episode ids in `evidence:` (semantic) or
   `derived_from:` (procedural). This is what stops the same cluster from
   being re-proposed forever, and what makes the claim auditable.
4. **Re-index.** `python -m mem index`.

```bash
python -m mem new semantic "Git hooks on this machine need LF line endings" \
  --tag deploy --tag git-hooks \
  --set kind=constraint --set confidence=0.95 \
  --set evidence=ep-20260826-deploy-hook-crlf,ep-20260812-hook-failed-on-clone
```

**Semantic or procedural?** If it describes the world, it is semantic. If it
tells you what to do when a condition holds, it is procedural. "Hooks need LF"
is a fact; "when a hook fails, check line endings first" is a habit. Most real
lessons produce both, and the procedure links to the fact.

**Merges and contradictions.** Two near-identical claims: merge into the
better-evidenced one and mark the other `superseded`, keeping `supersedes` on
the survivor. A wide confidence gap on near-identical claims usually means the
world changed — check which one is still true before merging.

---

## 3. Recall — before acting, not after

**When:** starting a task, hitting an error, or about to make a decision you
suspect you've made before. Recall is cheap; being wrong twice is not.

```bash
python -m mem recall "deploy hook failing" --balanced
python -m mem recall "deploy hook failing" --explain   # see the score components
```

`--balanced` returns a working set with a deliberate shape — roughly one
procedure, two facts, two episodes — rather than the flat top-N, which on a
mature store is five episodes about the same incident.

**Read the layers differently:**

- A **procedure** is a suggestion to follow, conditional on its trigger
  actually matching. Check `confidence` and the run counts; a `draft` with no
  runs is a hypothesis.
- A **fact** is a constraint on the plan. Check its `## Scope` before relying
  on it — that section exists to tell you when it has expired.
- An **episode** is grounding. Use it to notice how this case differs, not as
  a rule.

**When recall returns nothing:** that is information. Either this is genuinely
new — in which case there's an episode to write when it resolves — or the
memory that would have helped was filed under words you no longer use.

---

## 4. Reinforce and forget — closing the loop

A procedure that is never scored is a guess with good formatting.

```bash
python -m mem reinforce pr-fix-windows-git-hook success
python -m mem reinforce pr-fix-windows-git-hook failure
```

This is the only mechanism in the system that lets memory be *wrong and find
out*. Confidence follows the observed success rate, retrieval weights it, and
a procedure that keeps failing sinks on its own without anyone adjudicating.

A failure is also an episode. Write it, tag it like the others, and let it
feed the next consolidation — that is how a procedure gets amended rather than
merely demoted.

**Forgetting** is a move, never a delete:

```bash
python -m mem archive ep-20250101-trivial-thing --reason "superseded by se-git-hooks-need-lf"
python -m mem restore ep-20250101-trivial-thing
```

Consolidation nominates candidates: episodes older than 120 days with salience
below 0.4 that nothing cites, and semantic records unrevised for a year at
confidence below 0.5. Both are prompts to look, not verdicts. The stale-fact
case usually wants reconfirmation rather than archiving — check whether it is
still true and bump `updated`.

---

## Cadence

| Trigger | Action |
|---|---|
| Correction, surprise, or diagnosed failure | `mem new episodic` |
| Starting a task, or hitting a familiar error | `mem recall --balanced` |
| Finishing a procedure you recalled | `mem reinforce <id> success\|failure` |
| End of a substantial session | `mem consolidate` |
| Monthly, or when the store feels noisy | `mem stats`, then act on the decay list |
| After editing records by hand | `mem index && mem validate --strict` |

## Anti-patterns

- **Writing the conclusion without the episode.** A fact with no evidence
  can't be checked, and can't be un-learned.
- **Promoting on the first occurrence.** Once is an event. Three times is a
  pattern. The `min_support` default is 3 for a reason; lower it deliberately,
  not habitually.
- **Editing a fact in place when the world changed.** Supersede it. The old
  record explains why you believed the old thing, which is often the more
  useful memory.
- **Salience inflation.** If everything is 0.9, ranking has nothing left to
  say and you have re-invented the flat pile.
- **Storing what the repo stores.** Code structure, past diffs, config values.
  Memory is for what you cannot re-derive by looking.
