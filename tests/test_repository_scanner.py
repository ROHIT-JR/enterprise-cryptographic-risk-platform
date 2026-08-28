import zipfile
from pathlib import Path

import pytest

from scanners.archive import safe_extract_zip
from scanners.exceptions import UnsafeArchiveError
from scanners.repository import RepositoryScanner


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
    assert result.metadata["files_scanned"] == 2
    assert any(edge.relationship_type == "USES" for edge in result.relationships)


def test_safe_extract_rejects_zip_slip(tmp_path: Path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../../escape.py", "print('unsafe')")

    with pytest.raises(UnsafeArchiveError, match="Unsafe archive path"):
        safe_extract_zip(archive, tmp_path / "out")
