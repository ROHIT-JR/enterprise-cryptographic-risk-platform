from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from scanners.archive import safe_extract_zip
from scanners.base import ScanResult
from scanners.repository import RepositoryScanner


class SourceCodeScanner(RepositoryScanner):
    """Phase 1.5 repository scanner with a direct safe-ZIP entry point."""

    def scan_archive(
        self,
        archive: str | Path,
        *,
        display_name: str | None = None,
        max_files: int = 20_000,
        max_uncompressed_bytes: int = 250 * 1024 * 1024,
    ) -> ScanResult:
        archive_path = Path(archive)
        with TemporaryDirectory(prefix="ecdat-source-scan-") as temporary:
            extracted = safe_extract_zip(
                archive_path,
                Path(temporary) / "repository",
                max_files=max_files,
                max_uncompressed_bytes=max_uncompressed_bytes,
            )
            return self.scan_directory(
                extracted,
                display_name=display_name or archive_path.stem,
            )


SourceScanner = SourceCodeScanner

__all__ = ["SourceCodeScanner", "SourceScanner"]
