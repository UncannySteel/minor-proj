"""Minimal YAML-subset front matter, stdlib only.

The memory store is plain Markdown files with a `---` fenced header.  We
parse exactly the shapes the schemas use and nothing more:

    key: scalar          -> str | int | float | bool | None
    key: [a, b]          -> list
    key:                 -> list, optionally filled by following `- item` lines
      - a
      - b

Not supported (deliberately): nested mappings, anchors, multi-line scalars.
Keeping it this small means zero install steps and a parser you can read in
one sitting.  A string containing both quote characters is emitted with
double quotes and will not round-trip exactly; nothing in the schemas needs
that, and `validate` flags it.
"""
from __future__ import annotations

import re

DELIM = "---"
_NUM = re.compile(r"^-?\d+(\.\d+)?$")
_KEY = re.compile(r"^([A-Za-z0-9_.-]+):\s*(.*)$")
_UNSAFE_HEAD = set("[]{}#&*!|>%@`\"'-?:,")


def _scalar(raw):
    s = raw.strip()
    if not s:
        return ""
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    low = s.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "none", "~"):
        return None
    if _NUM.match(s):
        return float(s) if "." in s else int(s)
    return s


def _split_commas(s):
    parts, buf, quote = [], [], None
    for ch in s:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch == ",":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def _inline_list(raw):
    return [_scalar(p) for p in _split_commas(raw.strip()[1:-1])]


def loads(text):
    """Return ``(meta, body)``.  No header -> ``({}, text)``."""
    lines = text.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or lines[i].strip() != DELIM:
        return {}, text
    i += 1
    meta, key = {}, None
    while i < len(lines) and lines[i].strip() != DELIM:
        stripped = lines[i].strip()
        i += 1
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "-" or stripped.startswith("- "):
            if key is None:
                continue
            if not isinstance(meta.get(key), list):
                meta[key] = []
            meta[key].append(_scalar(stripped[1:]))
            continue
        m = _KEY.match(stripped)
        if not m:
            continue
        key, raw = m.group(1), m.group(2).strip()
        if raw.startswith("[") and raw.endswith("]"):
            meta[key] = _inline_list(raw)
        elif raw == "":
            meta[key] = []
        else:
            meta[key] = _scalar(raw)
    body = "\n".join(lines[i + 1:]).lstrip("\n")
    return meta, body


def _emit(v):
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    needs_quote = (
        s == ""
        or s != s.strip()
        or s[0] in _UNSAFE_HEAD
        or ": " in s
        or s.endswith(":")
        or bool(_NUM.match(s))
        or s.lower() in ("true", "false", "yes", "no", "null", "none", "~")
    )
    if not needs_quote:
        return s
    quote = "'" if '"' in s and "'" not in s else '"'
    return quote + s + quote


def dumps(meta, body="", order=()):
    """Serialize to a full Markdown document, keys in ``order`` first."""
    ordered = [k for k in order if k in meta]
    ordered += sorted(k for k in meta if k not in ordered)
    out = [DELIM]
    for k in ordered:
        v = meta[k]
        if isinstance(v, (list, tuple)):
            if not v:
                out.append(f"{k}: []")
            else:
                out.append(f"{k}:")
                out.extend(f"  - {_emit(x)}" for x in v)
        else:
            out.append(f"{k}: {_emit(v)}")
    out.append(DELIM)
    out.append("")
    out.append(body.strip("\n"))
    out.append("")
    return "\n".join(out)
