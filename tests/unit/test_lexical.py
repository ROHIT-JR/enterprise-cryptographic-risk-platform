"""Unit tests for the two structural fixes in scanners/lexical.py: joining a
statement whose arguments spread across lines, and resolving an import alias to its
canonical name before pattern matching. See scanners/lexical.py's module docstring
for what these deliberately do not handle.
"""

from __future__ import annotations

from scanners.lexical import find_import_aliases, logical_chunks, resolve_aliases


def _chunks_text(lines: list[str], language: str) -> list[str]:
    return [" ".join(lines[s : e + 1]) for s, e in logical_chunks(lines, language)]


# --- logical_chunks: single-line behaviour is unchanged -----------------------------
def test_single_line_statements_each_form_their_own_chunk():
    lines = ["import hashlib", "digest = hashlib.md5(payload).hexdigest()", ""]
    assert logical_chunks(lines, "python") == [(0, 0), (1, 1), (2, 2)]


# --- logical_chunks: the documented gap ("constructor call with args spread ------
# --- across lines") ------------------------------------------------------------------
def test_a_call_with_arguments_spread_across_lines_becomes_one_chunk():
    lines = [
        "cipher = AES.new(",
        "    key,",
        "    AES.MODE_GCM,",
        ")",
    ]
    assert logical_chunks(lines, "python") == [(0, 3)]
    assert _chunks_text(lines, "python") == ["cipher = AES.new(     key,     AES.MODE_GCM, )"]


def test_a_java_methods_opening_brace_does_not_merge_the_whole_method_body():
    # Regression: braces are block/scope delimiters in Java, not expression
    # continuations. Treating a method's `{` as "still open" merged two distinct
    # findings on different lines into a single chunk (caught by
    # test_india_payments_demo.py's real-fixture regression test).
    lines = [
        "public class LegacyCipher {",
        "    public byte[] encrypt(byte[] key) throws Exception {",
        '        Cipher cipher = Cipher.getInstance("DESede/CBC/PKCS5Padding");',
        "        return cipher.doFinal(key);",
        "    }",
        "    public byte[] decrypt(byte[] key) throws Exception {",
        '        Cipher cipher = Cipher.getInstance("DESede/CBC/PKCS5Padding");',
        "        return cipher.doFinal(key);",
        "    }",
        "}",
    ]
    chunks = logical_chunks(lines, "java")
    # Each statement is its own chunk; nothing spans from the class or method
    # opening brace down to its closing brace.
    assert (2, 2) in chunks
    assert (6, 6) in chunks
    assert not any(start <= 2 and end >= 6 for start, end in chunks)


def test_a_multiline_java_constructor_call_becomes_one_chunk():
    lines = [
        "Cipher cipher = Cipher.getInstance(",
        '    "AES/GCM/NoPadding"',
        ");",
    ]
    assert logical_chunks(lines, "java") == [(0, 2)]


def test_brackets_inside_a_string_literal_do_not_extend_the_chunk():
    # The "(" in the string must not be counted as an open bracket.
    lines = ['label = "starts with ("', "next_statement = 1"]
    assert logical_chunks(lines, "python") == [(0, 0), (1, 1)]


def test_a_python_triple_quoted_string_spanning_lines_is_one_chunk_and_not_bracket_counted():
    lines = [
        'doc = """',
        "an unmatched ( paren inside the docstring",
        '"""',
        "next_statement = 1",
    ]
    chunks = logical_chunks(lines, "python")
    assert chunks == [(0, 2), (3, 3)]


def test_python_trailing_backslash_continuation_forms_one_chunk():
    lines = ["value = 1 + \\", "    2"]
    assert logical_chunks(lines, "python") == [(0, 1)]


# --- find_import_aliases / resolve_aliases: the documented gap ("import hashlib -----
# --- as h; h.md5(...) won't match") --------------------------------------------------
def test_python_import_as_alias_is_found_and_resolved():
    lines = ["import hashlib as h", "digest = h.md5(payload).hexdigest()"]
    aliases = find_import_aliases(lines, "python")
    assert aliases == {"h": "hashlib"}
    assert "hashlib.md5" in resolve_aliases(lines[1], aliases)


def test_python_from_import_as_alias_is_found_and_resolved():
    lines = ["from Crypto.Cipher import AES as BlockCipher", "c = BlockCipher.new(key)"]
    aliases = find_import_aliases(lines, "python")
    assert aliases == {"BlockCipher": "AES"}
    assert "AES.new" in resolve_aliases(lines[1], aliases)


def test_js_destructured_import_alias_is_found_and_resolved():
    lines = ["import { createHash as hasher } from 'crypto';", "hasher('md5')"]
    aliases = find_import_aliases(lines, "javascript")
    assert aliases == {"hasher": "createHash"}
    assert "createHash(" in resolve_aliases(lines[1], aliases)


def test_js_require_property_alias_is_found_and_resolved():
    lines = ["const hasher = require('crypto').createHash;", "hasher('md5')"]
    aliases = find_import_aliases(lines, "javascript")
    assert aliases == {"hasher": "createHash"}
    assert "createHash(" in resolve_aliases(lines[1], aliases)


def test_resolve_aliases_only_replaces_whole_word_matches():
    # "h" must not match inside "hashlib" or "https" — only the bare identifier.
    aliases = {"h": "hashlib"}
    assert resolve_aliases("hashlib.sha256(); https_client.get()", aliases) == (
        "hashlib.sha256(); https_client.get()"
    )
    assert resolve_aliases("h.sha256()", aliases) == "hashlib.sha256()"


def test_no_aliases_found_for_an_unsupported_language_returns_empty_map():
    lines = ["import (\n\th \"crypto/sha256\"\n)"]
    assert find_import_aliases(lines, "go") == {}


def test_resolve_aliases_is_a_no_op_when_there_are_no_aliases():
    assert resolve_aliases("unchanged text", {}) == "unchanged text"
