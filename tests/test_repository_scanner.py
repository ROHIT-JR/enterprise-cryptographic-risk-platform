import zipfile
from pathlib import Path

import pytest

from scanners.archive import safe_extract_zip
from scanners.docker_scanner import DockerfileAnalyzer
from scanners.exceptions import UnsafeArchiveError
from scanners.repository import RepositoryScanner
from scanners.source_scanner import SourceCodeScanner


def test_repository_scanner_detects_algorithms_and_libraries(tmp_path: Path):
    (tmp_path / "auth.py").write_text(
        "from Crypto.PublicKey import RSA\n"
        "from Crypto.Cipher import AES\n"
        "key = RSA.generate(2048)\n"
        "cipher = AES.new(secret, AES.MODE_GCM)\n"
        "digest = hashlib.sha1(payload).digest()\n",
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text("pycryptodome==3.20.0\n", encoding="utf-8")

    result = RepositoryScanner().scan_directory(tmp_path, display_name="bank-auth")
    names = {asset.name for asset in result.assets}

    assert "RSA-2048" in names
    assert "AES" in names
    assert "SHA-1" in names
    assert "PyCryptodome" in names
    assert "PyCrypto" not in names
    assert result.metadata["files_scanned"] == 2
    assert any(edge.relationship_type == "USES" for edge in result.relationships)


def test_repository_scanner_detects_a_call_whose_arguments_spread_across_lines(tmp_path: Path):
    # docs/scanner-development.md's own named gap: "a constructor call with args
    # spread across lines is invisible" to a single-line regex pass.
    (tmp_path / "cipher.py").write_text(
        "cipher = AES.new(\n    key,\n    AES.MODE_GCM,\n)\n",
        encoding="utf-8",
    )

    result = RepositoryScanner().scan_directory(tmp_path, display_name="multiline")
    aes = next(asset for asset in result.assets if asset.name == "AES")

    assert aes.location == "cipher.py:1-4"
    assert aes.details["line"] == 1
    assert aes.details["end_line"] == 4


def test_repository_scanner_resolves_an_aliased_import(tmp_path: Path):
    # docs/scanner-development.md's own named gap: "import hashlib as h; h.md5(...)
    # won't match a pattern anchored on hashlib\.md5".
    (tmp_path / "legacy.py").write_text(
        "import hashlib as h\ndigest = h.md5(payload).hexdigest()\n",
        encoding="utf-8",
    )

    result = RepositoryScanner().scan_directory(tmp_path, display_name="aliased")
    md5 = next(asset for asset in result.assets if asset.name == "MD5")

    # The match came from the alias-resolved text, but the evidence shown is the
    # user's real, unmodified line — never a rewritten version of their code.
    assert "h.md5" in md5.evidence
    assert "hashlib.md5" not in md5.evidence
    assert md5.location == "legacy.py:2"


def test_repository_scanner_resolves_every_alias_in_a_multi_alias_import(tmp_path: Path):
    # Regression: only the first alias in a multi-alias import was resolved,
    # silently dropping DES here.
    (tmp_path / "ciphers.py").write_text(
        "from Crypto.Cipher import AES as A, DES as D\n"
        "c1 = A.new(key)\n"
        "c2 = D.new(key)\n",
        encoding="utf-8",
    )

    result = RepositoryScanner().scan_directory(tmp_path, display_name="multi-alias")
    names = {asset.name for asset in result.assets}

    assert "AES" in names
    assert "DES" in names


def test_repository_scanner_is_not_confused_by_a_windows_path_string(tmp_path: Path):
    # Regression: a string ending in an escaped backslash right before its closing
    # quote (e.g. a Windows path) was never recognised as closed, leaving the
    # "inside a string" state open for the rest of the file and merging two
    # distinct AES calls into a single reported finding.
    (tmp_path / "windows_paths.py").write_text(
        'LOG_DIR = "C:\\\\"\n'
        "cipher1 = AES.new(key1, AES.MODE_GCM)\n"
        "cipher2 = AES.new(key2, AES.MODE_GCM)\n",
        encoding="utf-8",
    )

    result = RepositoryScanner().scan_directory(tmp_path, display_name="windows-paths")
    aes_locations = {asset.location for asset in result.assets if asset.name == "AES"}

    assert aes_locations == {"windows_paths.py:2", "windows_paths.py:3"}


def test_source_scanner_covers_languages_libraries_and_dockerfile(tmp_path: Path):
    (tmp_path / "gateway.js").write_text(
        'import crypto from "node:crypto";\ncrypto.createHmac("sha512", secret);\n',
        encoding="utf-8",
    )
    (tmp_path / "native.c").write_text(
        "#include <openssl/evp.h>\nRSA_new();\nEVP_EncryptInit(ctx, cipher, 0, 0);\n",
        encoding="utf-8",
    )
    (tmp_path / "tls.conf").write_text(
        "ssl_protocols TLSv1.2 TLSv1.3;\nssl_certificate /tls/server.crt;\n",
        encoding="utf-8",
    )
    (tmp_path / "Dockerfile").write_text(
        "FROM ubuntu:24.04\nRUN apt-get install -y openssl libsodium\n",
        encoding="utf-8",
    )

    result = SourceCodeScanner().scan_directory(tmp_path)
    names = {asset.name for asset in result.assets}
    languages = {asset.details.get("language") for asset in result.assets}

    assert {"Node.js crypto", "HMAC", "SHA-512", "OpenSSL", "RSA", "AES"} <= names
    assert {"TLS 1.2", "TLS 1.3", "Configured TLS certificate", "libsodium"} <= names
    assert {"javascript", "c", "configuration", "dockerfile"} <= languages


def test_source_scanner_accepts_safe_zip_archive(tmp_path: Path):
    archive = tmp_path / "repository.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("service/auth.py", "from Crypto.Cipher import AES\nAES.new(key)\n")

    result = SourceCodeScanner().scan_archive(archive, display_name="secure-bank")

    assert result.target == "secure-bank"
    assert "AES" in {asset.name for asset in result.assets}


def test_dockerfile_analyzer_reports_base_image_and_crypto_packages():
    assets = DockerfileAnalyzer().analyze_text(
        "FROM python:3.12-slim\nRUN apt-get install -y openssl libssl-dev cryptopp\n"
    )

    assert {(asset.asset_type, asset.name) for asset in assets} == {
        ("application", "python:3.12-slim"),
        ("library", "OpenSSL"),
        ("library", "Crypto++"),
    }


def test_safe_extract_rejects_zip_slip(tmp_path: Path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../../escape.py", "print('unsafe')")

    with pytest.raises(UnsafeArchiveError, match="Unsafe archive path"):
        safe_extract_zip(archive, tmp_path / "out")
