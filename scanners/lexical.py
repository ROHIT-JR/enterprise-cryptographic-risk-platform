"""Two structural fixes for the regex scanner, both named as known gaps in
docs/scanner-development.md: multi-line statements are invisible to a single-line
regex pass, and an aliased import (``import hashlib as h``) doesn't match a pattern
anchored on the canonical name.

Neither function here is a parser. They are the "pragmatic middle ground" of joining
logical statements by tracking open brackets/strings, and of resolving the small set
of import-alias forms that are common in Python and JavaScript/TypeScript. A real
per-language AST (e.g. via tree-sitter) would close more gaps than this does — see
the "Known limitations" section below for exactly what is still missed.

Known limitations (deliberate, not oversights):
- Continuation without an open bracket (a bare trailing binary operator, e.g. a line
  ending in ``+`` with nothing open) is not tracked. Only Python's trailing ``\\`` and
  an open ``(``/``[`` (plus ``{`` in Python only, see next point) are continuations.
- ``{``/``}`` are only tracked as expression-continuation brackets in Python (dict/set
  literals). In every other language here they are almost always a block/scope
  delimiter (a class or method body, an ``if``/``for`` block), and an open method
  body would otherwise keep "the statement is still open" true for the method's
  entire length — merging every distinct finding inside it into one reported match.
  A multi-line object/array literal in JS/TS that relies solely on ``{`` (no ``(``)
  to signal continuation is the trade-off this makes; ``(``/``[`` still work there.
- Template-literal interpolation (`` `${...}` ``) is not bracket-tracked inside the
  template; a crypto call written entirely inside an interpolation on its own line
  could still be missed. This is rare in practice for the constructor-call pattern
  this fix targets.
- Import-alias resolution only understands Python's ``import X as Y`` / ``from X
  import Y as Z`` and JavaScript/TypeScript's ``import { X as Y } from '...'`` /
  ``const Y = require('...').X``. Go, Rust, PHP, C#, and Java's static-import forms
  are not covered here; add them alongside that language's own patterns.
- Alias resolution is a whole-file, whole-word text substitution, not scope-aware: a
  local variable that happens to share an alias's name in an unrelated scope would
  also be substituted. Given aliases are usually distinctive names chosen for an
  import, this is judged an acceptable, rare false-positive risk versus the false
  negatives it fixes.
"""

from __future__ import annotations

import re

_PY_IMPORT_LINE = re.compile(r"^\s*import\s+(.+)$")
_PY_FROM_IMPORT_LINE = re.compile(r"^\s*from\s+[\w.]+\s+import\s+(.+)$")
_PY_AS_ALIAS = re.compile(r"^\s*([\w.]+)\s+as\s+(\w+)\s*$")
_JS_IMPORT_BLOCK = re.compile(r"import\s*\{([^}]*)\}\s*from")
_JS_AS_ALIAS = re.compile(r"\b([\w$]+)\s+as\s+([\w$]+)")
_JS_REQUIRE_PROP_ALIAS = re.compile(
    r"(?:const|let|var)\s+([\w$]+)\s*=\s*require\(\s*['\"][^'\"]+['\"]\s*\)\.(\w+)"
)


def find_import_aliases(lines: list[str], language: str) -> dict[str, str]:
    """Scan every line once for an import-alias declaration.

    Returns {alias_identifier: canonical_identifier}. Only Python and
    JavaScript/TypeScript forms are recognised; every other language returns an
    empty map, so this is a strict no-op for them rather than a guess. A single
    import statement can alias more than one name (``import os, sys as s`` /
    ``from Crypto.Cipher import AES as A, DES as D`` / ``import { a as x, b as y }
    from '...'``) — every comma-separated item is checked, not just the first.
    """
    aliases: dict[str, str] = {}
    if language == "python":
        for raw in lines:
            line = raw.split("#", 1)[0]  # a trailing comment isn't part of the import list
            match = _PY_FROM_IMPORT_LINE.match(line)
            if match:
                for item in match.group(1).split(","):
                    alias_match = _PY_AS_ALIAS.match(item)
                    if alias_match:
                        name, alias = alias_match.groups()
                        aliases[alias] = name.rsplit(".", 1)[-1]
                continue
            match = _PY_IMPORT_LINE.match(line)
            if match:
                for item in match.group(1).split(","):
                    alias_match = _PY_AS_ALIAS.match(item)
                    if alias_match:
                        module, alias = alias_match.groups()
                        aliases[alias] = module.rsplit(".", 1)[-1]
    elif language in ("javascript", "typescript"):
        for line in lines:
            block = _JS_IMPORT_BLOCK.search(line)
            if block:
                for match in _JS_AS_ALIAS.finditer(block.group(1)):
                    name, alias = match.groups()
                    aliases[alias] = name
            match = _JS_REQUIRE_PROP_ALIAS.search(line)
            if match:
                alias, name = match.groups()
                aliases[alias] = name
    return aliases


def resolve_aliases(text: str, aliases: dict[str, str]) -> str:
    """Substitute known alias identifiers with their canonical name, for pattern
    matching only. Callers must keep the original text for display/evidence — a
    user should see the code they actually wrote, not a rewritten version of it.
    """
    if not aliases:
        return text
    for alias, canonical in aliases.items():
        text = re.sub(rf"\b{re.escape(alias)}\b", canonical, text)
    return text


# `(` / `[` mean "this expression continues" in every language here, so they're
# always tracked. `{` / `}` are NOT tracked for the C-family languages: there,
# braces overwhelmingly delimit a block/scope (a class or method body, an if/for
# block), and treating a method's opening brace as "the statement is still open"
# would merge every statement in the whole method into one chunk — collapsing
# distinct findings on different lines into a single reported match. Python uses
# `{}` for dict/set literals, which genuinely can span lines as part of one
# expression, so Python keeps them tracked.
_BRACE_TRACKING_LANGUAGES = {"python"}
_OPENERS = "(["
_CLOSERS = ")]"
StringState = tuple[str, bool] | None  # (quote_char, is_triple_or_template) or None


def _is_escaped(line: str, i: int) -> bool:
    """True if line[i] is escaped by an odd-length run of backslashes immediately
    before it. A single preceding ``\\`` escapes it, but ``\\\\`` is an escaped
    backslash followed by an *unescaped* line[i] (e.g. the closing quote of the
    Windows-path string ``"C:\\\\"``) — counting the whole run, not just the one
    character before it, is what tells the two cases apart.
    """
    count = 0
    j = i - 1
    while j >= 0 and line[j] == "\\":
        count += 1
        j -= 1
    return count % 2 == 1


def _line_bracket_delta(
    line: str, string_state: StringState, track_braces: bool
) -> tuple[int, StringState]:
    """Net bracket delta for one line, skipping characters inside a string literal
    (including one already open going into this line), and the string state to
    carry into the next line.
    """
    openers = _OPENERS + "{" if track_braces else _OPENERS
    closers = _CLOSERS + "}" if track_braces else _CLOSERS
    delta = 0
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if string_state is not None:
            quote, triple = string_state
            if triple and line[i : i + 3] == quote * 3 and not _is_escaped(line, i):
                i += 3
                string_state = None
                continue
            if not triple and ch == quote and not _is_escaped(line, i):
                i += 1
                string_state = None
                continue
            i += 1
            continue
        if line[i : i + 3] in ('"""', "'''"):
            string_state = (line[i], True)
            i += 3
            continue
        if ch in ("\"", "'", "`"):
            string_state = (ch, False)
            i += 1
            continue
        if ch in openers:
            delta += 1
        elif ch in closers:
            delta -= 1
        i += 1
    return delta, string_state


def logical_chunks(lines: list[str], language: str) -> list[tuple[int, int]]:
    """Group 0-based line indices into logical statements.

    A chunk keeps extending while bracket depth is above zero, a multi-line string
    is still open, or (Python only) the line ends with a continuation backslash.
    Every line belongs to exactly one chunk, in order, so this is always safe to
    iterate as a drop-in replacement for scanning one line at a time.
    """
    chunks: list[tuple[int, int]] = []
    track_braces = language in _BRACE_TRACKING_LANGUAGES
    depth = 0
    string_state: StringState = None
    start = 0
    for idx, line in enumerate(lines):
        line_delta, string_state = _line_bracket_delta(line, string_state, track_braces)
        depth += line_delta
        continues = (
            depth > 0
            or string_state is not None
            or (language == "python" and line.rstrip().endswith("\\"))
        )
        if not continues:
            chunks.append((start, idx))
            start = idx + 1
            depth = 0
    if start < len(lines):
        chunks.append((start, len(lines) - 1))
    return chunks
