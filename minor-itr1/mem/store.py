"""The file-backed record store.

Layout under ``<root>/memory``::

    episodic/<YYYY-MM>/ep-<date>-<slug>.md    bucketed, because episodes pile up
    semantic/se-<slug>.md                     flat, because ids are addresses
    procedural/pr-<slug>.md                   flat, same reason
    _archive/<layer>/...                      forgotten, not deleted

Every record is a Markdown file a human can open and edit by hand. The tools
here never hold a lock and never rewrite a file they did not parse first.
"""
from __future__ import annotations

import datetime as dt
import os
import shutil
from pathlib import Path

from . import frontmatter, schema

MEMORY_DIRNAME = "memory"
ARCHIVE_DIRNAME = "_archive"
INDEX_DIRNAME = "index"


class Record:
    """One memory file: parsed front matter plus Markdown body."""

    __slots__ = ("meta", "body", "path")

    def __init__(self, meta, body="", path=None):
        self.meta = dict(meta)
        self.body = body or ""
        self.path = Path(path) if path else None

    # -- identity -------------------------------------------------------
    @property
    def id(self):
        return self.meta.get("id")

    @property
    def layer(self):
        return self.meta.get("layer")

    @property
    def title(self):
        return self.meta.get("title", "")

    @property
    def tags(self):
        return list(self.meta.get("tags") or [])

    @property
    def links(self):
        out = list(self.meta.get("links") or [])
        out += list(self.meta.get("evidence") or [])
        out += list(self.meta.get("derived_from") or [])
        out += list(self.meta.get("uses") or [])
        out += list(self.meta.get("supersedes") or [])
        seen, ordered = set(), []
        for link in out:
            key = str(link).strip("[] ")
            if key and key not in seen:
                seen.add(key)
                ordered.append(key)
        return ordered

    # -- serialisation --------------------------------------------------
    def to_text(self):
        order = schema.FIELD_ORDER.get(self.layer, ())
        return frontmatter.dumps(self.meta, self.body, order=order)

    @classmethod
    def from_text(cls, text, path=None):
        meta, body = frontmatter.loads(text)
        return cls(meta, body, path)

    def touch(self, when=None):
        if self.layer != "episodic":
            self.meta["updated"] = schema.now_iso(when)
        return self

    def validate(self):
        return schema.validate(self.meta, self.body)

    def __repr__(self):  # pragma: no cover - debugging aid
        return "<Record %s %r>" % (self.id, self.title)


class Store:
    """Reads and writes records under a root directory."""

    def __init__(self, root=None):
        self.root = Path(root or default_root()).resolve()
        self.memory = self.root / MEMORY_DIRNAME
        self.archive = self.memory / ARCHIVE_DIRNAME
        self.index_dir = self.root / INDEX_DIRNAME
        self._errors = None

    @property
    def errors(self):
        """Lazy so importing the store never touches the filesystem."""
        if self._errors is None:
            from .errorlog import ErrorLog
            self._errors = ErrorLog(self.root)
        return self._errors

    # -- layout ---------------------------------------------------------
    def init(self):
        for layer in schema.LAYERS:
            (self.memory / layer).mkdir(parents=True, exist_ok=True)
            (self.archive / layer).mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        return self

    def layer_dir(self, layer, when=None, archived=False):
        base = (self.archive if archived else self.memory) / layer
        if layer == "episodic" and not archived:
            stamp = schema.parse_ts(when) if when else dt.datetime.now(dt.timezone.utc)
            base = base / (stamp or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m")
        return base

    def relpath(self, path):
        try:
            return str(Path(path).resolve().relative_to(self.root)).replace(os.sep, "/")
        except ValueError:
            return str(path)

    # -- ids ------------------------------------------------------------
    def new_id(self, layer, title, when=None):
        """Stable, human-typable id. Episodes carry their date; the durable
        layers do not, so ``se-user-prefers-plain-english`` stays quotable."""
        slug = schema.slugify(title)
        prefix = schema.PREFIX[layer]
        if layer == "episodic":
            stamp = schema.parse_ts(when) or dt.datetime.now(dt.timezone.utc)
            base = "%s-%s-%s" % (prefix, stamp.strftime("%Y%m%d"), slug)
        else:
            base = "%s-%s" % (prefix, slug)
        candidate, n = base, 2
        while self.get(candidate) is not None:
            candidate = "%s-%d" % (base, n)
            n += 1
        return candidate

    # -- read -----------------------------------------------------------
    def load(self, path):
        path = Path(path)
        return Record.from_text(path.read_text(encoding="utf-8"), path)

    def paths(self, layers=None, include_archived=False):
        layers = tuple(layers or schema.LAYERS)
        roots = [self.memory / layer for layer in layers]
        if include_archived:
            roots += [self.archive / layer for layer in layers]
        for base in roots:
            if not base.exists():
                continue
            for path in sorted(base.rglob("*.md")):
                yield path

    def records(self, layers=None, include_archived=False):
        for path in self.paths(layers, include_archived):
            try:
                record = self.load(path)
            except (OSError, UnicodeDecodeError) as exc:
                # An unreadable file must not abort a walk, but it must not
                # vanish either - a silently skipped record is a lost memory.
                self.errors.exception(exc, kind="store.load",
                                      path=self.relpath(path))
                continue
            if record.layer:
                yield record

    def get(self, rec_id, include_archived=True):
        if not rec_id:
            return None
        rec_id = str(rec_id).strip("[] ")
        layer = schema.LAYER_BY_PREFIX.get(rec_id.split("-", 1)[0])
        layers = (layer,) if layer else schema.LAYERS
        for path in self.paths(layers, include_archived=include_archived):
            if path.stem == rec_id:
                return self.load(path)
        return None

    # -- write ----------------------------------------------------------
    def create(self, layer, title, body=None, when=None, **extra):
        meta = schema.default_meta(layer, title, when)
        meta.update({k: v for k, v in extra.items() if v is not None})
        meta.setdefault("id", self.new_id(layer, title, meta.get("occurred") or when))
        if body is None:
            body = schema.TEMPLATES[layer]
        record = Record(meta, body)
        record.path = self.path_for(record)
        return self.save(record)

    def path_for(self, record):
        directory = self.layer_dir(record.layer, record.meta.get("occurred"))
        return directory / ("%s.md" % record.id)

    def save(self, record):
        if not record.id:
            raise ValueError("record has no id")
        path = Path(record.path) if record.path else self.path_for(record)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".md.tmp")
        tmp.write_text(record.to_text(), encoding="utf-8")
        os.replace(tmp, path)
        record.path = path
        return record

    def archive_record(self, rec_id, reason="", when=None):
        """Forgetting is a move, never a delete: the trail stays auditable."""
        record = self.get(rec_id, include_archived=False)
        if record is None:
            return None
        record.meta["status"] = "archived"
        record.meta["archived"] = schema.now_iso(when)
        if reason:
            record.meta["archive_reason"] = reason
        target_dir = self.layer_dir(record.layer, archived=True)
        target_dir.mkdir(parents=True, exist_ok=True)
        old_path = record.path
        record.path = target_dir / ("%s.md" % record.id)
        self.save(record)
        if old_path and Path(old_path).exists():
            Path(old_path).unlink()
        return record

    def restore(self, rec_id):
        record = self.get(rec_id)
        if record is None or ARCHIVE_DIRNAME not in Path(record.path).parts:
            return None
        old_path = record.path
        record.meta["status"] = "active"
        record.meta.pop("archived", None)
        record.meta.pop("archive_reason", None)
        record.path = self.path_for(record)
        self.save(record)
        Path(old_path).unlink()
        return record

    def wipe(self):  # pragma: no cover - used by fixtures and demos
        for name in (MEMORY_DIRNAME, INDEX_DIRNAME):
            shutil.rmtree(self.root / name, ignore_errors=True)
        return self.init()


def default_root():
    """``MEM_ROOT`` if set, else the directory holding this package."""
    env = os.environ.get("MEM_ROOT")
    return Path(env) if env else Path(__file__).resolve().parent.parent
