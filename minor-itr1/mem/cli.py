"""``python -m mem <command>`` - the whole framework from one entry point."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from . import consolidate as consolidate_mod
from . import errorlog as errorlog_mod
from . import index as index_mod
from . import migrate as migrate_mod
from . import recall as recall_mod
from . import schema
from .store import Store, default_root


def _store(args):
    return Store(getattr(args, "root", None) or default_root())


def _kv(pairs):
    """``--set key=value`` with light type coercion, lists via ``a,b,c``."""
    out = {}
    for item in pairs or []:
        if "=" not in item:
            raise SystemExit("--set expects key=value, got %r" % item)
        key, _, raw = item.partition("=")
        key = key.strip()
        if key in schema.LIST_FIELDS:
            out[key] = [p.strip() for p in raw.split(",") if p.strip()]
        elif key in schema.UNIT_FIELDS or key in ("runs", "successes", "failures"):
            try:
                out[key] = float(raw) if "." in raw else int(raw)
            except ValueError:
                raise SystemExit("%s must be numeric, got %r" % (key, raw))
        else:
            out[key] = raw
    return out


# -- commands -----------------------------------------------------------

def cmd_init(args):
    store = _store(args).init()
    index_mod.save(store)
    print("initialised memory store at %s" % store.root)
    for layer in schema.LAYERS:
        print("  memory/%s/" % layer)
    return 0


def cmd_new(args):
    store = _store(args).init()
    body = args.body
    if body == "-":
        body = sys.stdin.read()
    extra = _kv(args.set)
    if args.tag:
        extra["tags"] = sorted(set(list(extra.get("tags", [])) + args.tag))
    if args.link:
        extra["links"] = sorted(set(list(extra.get("links", [])) + args.link))
    record = store.create(args.layer, args.title, body=body, **extra)
    errors, warnings = record.validate()
    print("wrote %s" % store.relpath(record.path))
    for problem in errors:
        print("  error:   %s" % problem)
    for problem in warnings:
        print("  warning: %s" % problem)
    if not args.no_index:
        index_mod.save(store)
    return 1 if errors else 0


def cmd_recall(args):
    store = _store(args)
    query = " ".join(args.query)
    if args.balanced:
        hits = recall_mod.working_set(store, query, budget=args.k)
    else:
        hits = recall_mod.search(store, query, k=args.k,
                                 layers=args.layer or None,
                                 include_archived=args.archived)
    if args.json:
        print(json.dumps([h.as_dict() for h in hits], indent=2))
    else:
        print(recall_mod.render(hits, explain=args.explain))
    return 0


def cmd_show(args):
    store = _store(args)
    record = store.get(args.id)
    if record is None:
        print("no record with id %r" % args.id, file=sys.stderr)
        return 1
    print(record.to_text())
    return 0


def cmd_index(args):
    store = _store(args).init()
    data = index_mod.save(store, include_archived=args.archived)
    print("indexed %d records -> %s" % (data["count"], store.relpath(store.index_dir)))
    for layer, count in sorted(data["counts_by_layer"].items()):
        print("  %-11s %d" % (layer, count))
    return 0


def cmd_validate(args):
    store = _store(args)
    bad = 0
    for record in store.records(include_archived=args.archived):
        errors, warnings = record.validate()
        if errors or (warnings and args.strict):
            bad += 1
        for problem in errors:
            print("error   %s: %s" % (record.id, problem))
        if args.strict:
            for problem in warnings:
                print("warning %s: %s" % (record.id, problem))
    print("%d record(s) with problems" % bad)
    return 1 if bad else 0


def cmd_consolidate(args):
    store = _store(args)
    report = consolidate_mod.analyze(store, min_support=args.min_support)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(consolidate_mod.render(report, verbose=args.verbose))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(consolidate_mod.render(report, verbose=True))
        print("\nreport written to %s" % args.out)
    return 0


def cmd_archive(args):
    store = _store(args)
    record = store.archive_record(args.id, reason=args.reason)
    if record is None:
        print("no active record with id %r" % args.id, file=sys.stderr)
        return 1
    print("archived %s -> %s" % (args.id, store.relpath(record.path)))
    index_mod.save(store)
    return 0


def cmd_restore(args):
    store = _store(args)
    record = store.restore(args.id)
    if record is None:
        print("no archived record with id %r" % args.id, file=sys.stderr)
        return 1
    print("restored %s -> %s" % (args.id, store.relpath(record.path)))
    index_mod.save(store)
    return 0


def cmd_reinforce(args):
    """Record that a procedure ran, and whether it worked."""
    store = _store(args)
    record = store.get(args.id)
    if record is None or record.layer != "procedural":
        print("no procedural record with id %r" % args.id, file=sys.stderr)
        return 1
    record.meta["runs"] = int(record.meta.get("runs") or 0) + 1
    key = "successes" if args.outcome == "success" else "failures"
    record.meta[key] = int(record.meta.get(key) or 0) + 1
    ok = int(record.meta.get("successes") or 0)
    total = max(1, ok + int(record.meta.get("failures") or 0))
    # Confidence tracks the observed success rate, damped toward the prior.
    record.meta["confidence"] = round(0.3 * 0.6 + 0.7 * (ok / total), 3)
    if record.meta.get("status") == "draft" and ok >= 2:
        record.meta["status"] = "active"
    record.touch()
    store.save(record)
    print("%s: runs=%s successes=%s failures=%s confidence=%s status=%s" % (
        record.id, record.meta["runs"], record.meta.get("successes", 0),
        record.meta.get("failures", 0), record.meta["confidence"],
        record.meta.get("status")))
    index_mod.save(store)
    return 0


def cmd_stats(args):
    store = _store(args)
    data = index_mod.load(store)
    records = data["records"]
    print("root: %s" % store.root)
    print("records: %d (%s)" % (
        len(records),
        ", ".join("%s %s" % (v, k) for k, v in sorted(data["counts_by_layer"].items()))
        or "empty"))
    if not records:
        return 0
    linked = sum(1 for e in records if e["links"])
    print("linked: %d/%d (%.0f%%)" % (linked, len(records), 100.0 * linked / len(records)))
    print("mean salience: %.2f   mean confidence: %.2f" % (
        sum(e["salience"] for e in records) / len(records),
        sum(e["confidence"] for e in records) / len(records)))
    tags = Counter(t for e in records for t in e["tags"])
    if tags:
        print("top tags: %s" % ", ".join("%s(%d)" % (t, c) for t, c in tags.most_common(8)))
    statuses = Counter(e["status"] for e in records)
    print("status: %s" % ", ".join("%s %s" % (v, k) for k, v in sorted(statuses.items())))
    return 0


def cmd_errors(args):
    log = errorlog_mod.ErrorLog(getattr(args, "root", None) or default_root())
    if args.clear:
        print("cleared %s" % log.path if log.clear() else "nothing to clear")
        return 0
    if args.stats:
        data = log.stats(min_recurrence=args.min_recurrence)
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(errorlog_mod.render_stats(data, args.min_recurrence))
        return 0
    rows = log.entries(limit=args.tail, kind=args.kind, severity=args.severity,
                       fingerprint=args.fingerprint, since=args.since)
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(errorlog_mod.render(rows, verbose=args.verbose))
    return 0


def cmd_migrate(args):
    store = _store(args)
    proposals = migrate_mod.plan(args.source)
    if not proposals:
        print("nothing to migrate from %s" % args.source)
        return 0
    print(migrate_mod.render(proposals))
    if not args.apply:
        print("\ndry run - re-run with --apply to write %d record(s)" % len(proposals))
        return 0
    store.init()
    written = migrate_mod.apply(store, proposals)
    print("\nwrote %d record(s)" % len(written))
    index_mod.save(store)
    return 0


# -- parser -------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="mem", description="Layered memory: episodic, semantic, procedural.")
    parser.add_argument("--root", help="store root (default: MEM_ROOT or the package parent)")
    subs = parser.add_subparsers(dest="command", required=True)

    p = subs.add_parser("init", help="create the directory layout")
    p.set_defaults(func=cmd_init)

    p = subs.add_parser("new", help="write a record")
    p.add_argument("layer", choices=schema.LAYERS)
    p.add_argument("title")
    p.add_argument("--body", default=None, help="body text, or '-' to read stdin")
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--link", action="append", default=[])
    p.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    p.add_argument("--no-index", action="store_true")
    p.set_defaults(func=cmd_new)

    p = subs.add_parser("recall", help="rank records against a query")
    p.add_argument("query", nargs="+")
    p.add_argument("-k", type=int, default=8)
    p.add_argument("--layer", action="append", choices=schema.LAYERS)
    p.add_argument("--balanced", action="store_true",
                   help="quota one slice per layer instead of a flat top-k")
    p.add_argument("--explain", action="store_true", help="show score components")
    p.add_argument("--archived", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_recall)

    p = subs.add_parser("show", help="print one record")
    p.add_argument("id")
    p.set_defaults(func=cmd_show)

    p = subs.add_parser("index", help="rebuild index/index.json and index/MEMORY.md")
    p.add_argument("--archived", action="store_true")
    p.set_defaults(func=cmd_index)

    p = subs.add_parser("validate", help="check every record against its schema")
    p.add_argument("--strict", action="store_true", help="treat warnings as problems")
    p.add_argument("--archived", action="store_true")
    p.set_defaults(func=cmd_validate)

    p = subs.add_parser("consolidate", help="propose promotions, merges and forgetting")
    p.add_argument("--min-support", type=int, default=consolidate_mod.MIN_SUPPORT)
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--out", help="also write the full report to this path")
    p.set_defaults(func=cmd_consolidate)

    p = subs.add_parser("archive", help="move a record out of active memory")
    p.add_argument("id")
    p.add_argument("--reason", default="")
    p.set_defaults(func=cmd_archive)

    p = subs.add_parser("restore", help="bring an archived record back")
    p.add_argument("id")
    p.set_defaults(func=cmd_restore)

    p = subs.add_parser("reinforce", help="log a procedure run and update its confidence")
    p.add_argument("id")
    p.add_argument("outcome", choices=("success", "failure"))
    p.set_defaults(func=cmd_reinforce)

    p = subs.add_parser("stats", help="store health at a glance")
    p.set_defaults(func=cmd_stats)

    p = subs.add_parser("errors", help="read the structured error log")
    p.add_argument("--tail", type=int, default=20, help="show the last N entries")
    p.add_argument("--kind")
    p.add_argument("--severity", choices=errorlog_mod.SEVERITIES)
    p.add_argument("--fingerprint", help="show every occurrence of one failure shape")
    p.add_argument("--since", help="ISO-8601 cutoff, e.g. 2026-09-01")
    p.add_argument("--stats", action="store_true", help="counts and recurring failures")
    p.add_argument("--min-recurrence", type=int, default=3)
    p.add_argument("--verbose", action="store_true", help="include tracebacks")
    p.add_argument("--clear", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_errors)

    p = subs.add_parser("migrate", help="import a flat memory directory into the layers")
    p.add_argument("source", help="directory of flat .md memory files")
    p.add_argument("--apply", action="store_true", help="write (default is a dry run)")
    p.set_defaults(func=cmd_migrate)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    log = errorlog_mod.ErrorLog(getattr(args, "root", None) or default_root())
    try:
        return args.func(args) or 0
    except SystemExit:
        raise
    except Exception as exc:  # logged, then surfaced - never swallowed
        log.exception(exc, kind="cli", command=args.command)
        print("error: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        print("logged to %s (see `mem errors --tail 1 --verbose`)" % log.path,
              file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
