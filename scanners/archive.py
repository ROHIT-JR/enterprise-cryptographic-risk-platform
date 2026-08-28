from __future__ import annotations

import shutil
import stat
import zipfile
from pathlib import Path

from scanners.exceptions import UnsafeArchiveError


def safe_extract_zip(
    archive: Path,
    destination: Path,
    *,
    max_files: int = 20_000,
    max_uncompressed_bytes: int = 250 * 1024 * 1024,
) -> Path:
    """Extract a ZIP while rejecting traversal, symlinks, bombs, and encrypted entries."""

    destination.mkdir(parents=True, exist_ok=True)
    destination_root = destination.resolve()

    try:
        bundle = zipfile.ZipFile(archive)
    except zipfile.BadZipFile as exc:
        raise UnsafeArchiveError("The upload is not a valid ZIP archive") from exc

    with bundle:
        members = bundle.infolist()
        if len(members) > max_files:
            raise UnsafeArchiveError(f"Archive contains more than {max_files:,} entries")

        total_size = sum(member.file_size for member in members)
        if total_size > max_uncompressed_bytes:
            raise UnsafeArchiveError(
                f"Archive expands beyond {max_uncompressed_bytes // (1024 * 1024)} MiB"
            )

        for member in members:
            if member.flag_bits & 0x1:
                raise UnsafeArchiveError("Encrypted ZIP entries are not supported")
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise UnsafeArchiveError(f"Symbolic links are not allowed: {member.filename}")

            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise UnsafeArchiveError(f"Unsafe archive path: {member.filename}")
            output_path = (destination_root / member_path).resolve()
            if not output_path.is_relative_to(destination_root):
                raise UnsafeArchiveError(f"Unsafe archive path: {member.filename}")

            if member.is_dir():
                output_path.mkdir(parents=True, exist_ok=True)
                continue
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, output_path.open("wb") as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)

    children = [path for path in destination.iterdir() if path.name != "__MACOSX"]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return destination
