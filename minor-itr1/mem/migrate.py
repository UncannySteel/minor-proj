"""Import a flat, single-tier memory directory into the three layers.

The existing convention is one fact per file with a ``type`` of user,
feedback, project or reference. That maps cleanly onto the layers:

    user       -> semantic / preference   (who the person is, what they want)
    reference  -> semantic / reference    (a pointer that stays true)
    project    -> semantic / project      (state of ongoing work)
    feedback   -> procedural              (guidance is a rule for acting)

Feedback is the interesting case: "prefer X because Y" is not a fact, it is a
procedure with a trigger and a verification. Migrating it into the procedural
layer is the whole point of having three layers.

Nothing is written without ``--apply``, and the source directory is never
modified.
"""
from __future__ import annotations

from pathlib import Path

from . import frontmatter, schema

TYPE_MAP = {
    "user": ("semantic", "preference"),
    "reference": ("semantic", "reference"),
    "project": ("semantic", "project"),
    "feedback": ("procedural", None),
}
DEFAULT_TARGET = ("semantic", "fact")
SKIP_NAMES = {"memory.md", "readme.md", "index.md"}


def _detect_type(meta):
    """Read ``type:`` wherever it sits - flat, or nested under ``metadata:``."""
    for key in ("type", "metadata.type", "kind", "layer"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return ""


def plan(source):
    """Return a list of proposals; reads the source, writes nothing."""
    src = Path(source)
    if not src.exists():
        raise SystemExit("source directory not found: %s" % src)

    proposals = []
    for path in sorted(src.rglob("*.md")):
        if path.name.lower() in SKIP_NAMES:
            continue
        try:
            meta, body = frontmatter.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        source_type = _detect_type(meta)
        layer, kind = TYPE_MAP.get(source_type, DEFAULT_TARGET)
        title = str(meta.get("title") or meta.get("name") or path.stem).replace("-", " ").strip()
        proposals.append({
            "source_path": str(path),
            "source_type": source_type or "(none)",
            "layer": layer,
            "kind": kind,
            "title": title.capitalize(),
            "description": str(meta.get("description") or ""),
            "body": _reshape(layer, body, meta),
            "tags": sorted(set(list(meta.get("tags") or []) +
                               ([source_type] if source_type else []))),
        })
    return proposals


def _reshape(layer, body, meta):
    """Wrap the original prose in the target layer's section headings.

    The original text is preserved verbatim under the heading; anything the
    new schema wants but the old file never had is left as an explicit
    placeholder rather than invented.
    """
    body = (body or "").strip()
    note = str(meta.get("description") or "").strip()
    if layer == "procedural":
        return (
            "## Trigger\n\n%s\n\n"
            "## Steps\n\n%s\n\n"
            "## Verification\n\n<TODO: what observable says this was followed?>\n\n"
            "## Failure modes\n\n- <TODO: fill in from the next time this misfires>\n"
            % (note or "<TODO: when should this fire?>", body or "<TODO>")
        )
    return (
        "## Claim\n\n%s\n\n"
        "## Scope\n\n%s\n\n"
        "## Evidence\n\n- imported from %s (pre-layer memory; no episode on file)\n"
        % (body or note or "<TODO>",
           note or "<TODO: when does this stop being true?>",
           meta.get("name") or "flat memory")
    )


def render(proposals):
    lines = ["# Migration plan", "", "%d file(s):" % len(proposals), ""]
    for item in proposals:
        target = "%s/%s" % (item["layer"], item["kind"] or "-")
        lines.append("- %-34s %-22s <- %s"
                     % (item["title"][:34], target, Path(item["source_path"]).name))
    lines += ["", "Bodies are reshaped into the target sections with the original"
                  " prose kept verbatim; missing fields become explicit TODOs"
                  " rather than inventions.", ""]
    return "\n".join(lines)


def apply(store, proposals):
    written = []
    for item in proposals:
        extra = {"tags": item["tags"], "source": "imported"}
        if item["kind"]:
            extra["kind"] = item["kind"]
        if item["layer"] == "procedural":
            extra["trigger"] = item["description"] or item["title"]
            extra["status"] = "draft"  # imported guidance is unproven here
        record = store.create(item["layer"], item["title"],
                              body=item["body"], **extra)
        record.meta["imported_from"] = str(Path(item["source_path"]).name)
        record.meta["confidence"] = 0.6
        store.save(record)
        written.append(record)
    return written


def summarize_layers():  # pragma: no cover - documentation helper
    return {src: "%s%s" % (layer, "/" + kind if kind else "")
            for src, (layer, kind) in TYPE_MAP.items()}


assert set(TYPE_MAP) <= {"user", "reference", "project", "feedback"}
assert all(layer in schema.LAYERS for layer, _ in TYPE_MAP.values())
