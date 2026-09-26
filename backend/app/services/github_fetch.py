from __future__ import annotations

import ipaddress
import re
import socket
from pathlib import Path
from urllib.parse import urlparse

import httpx

from backend.app.config import get_settings

_GITHUB_HOST = "github.com"
_CODELOAD_HOST = "codeload.github.com"
_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


class InvalidRepositoryUrlError(ValueError):
    """Raised for any URL, redirect, or archive that fails validation."""


def parse_github_repo_url(url: str) -> tuple[str, str]:
    """Extract ``(owner, repo)`` from a ``https://github.com/<owner>/<repo>`` URL.

    Only github.com is accepted — the backend never fetches an arbitrary
    user-supplied host, which is what keeps this feature's SSRF surface small.
    """
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or parsed.netloc.lower() != _GITHUB_HOST:
        raise InvalidRepositoryUrlError("Only https://github.com/<owner>/<repo> URLs are supported")
    parts = [segment for segment in parsed.path.split("/") if segment]
    if len(parts) < 2:
        raise InvalidRepositoryUrlError("URL must include an owner and a repository name")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    if not _NAME_RE.match(owner) or not _NAME_RE.match(repo):
        raise InvalidRepositoryUrlError("Repository owner/name contains unsupported characters")
    return owner, repo


def _assert_resolves_public(host: str) -> None:
    """Reject DNS answers that point at a private/loopback/link-local address.

    ``codeload.github.com`` is a fixed, trusted hostname — never user input —
    so this isn't guarding against a user picking a malicious target. It's
    defense in depth against DNS poisoning/rebinding pointing the archive
    download at an internal address. Mirrors ``TLSScanner._resolve``.
    """
    settings = get_settings()
    if settings.tls_allow_private_targets:
        return
    try:
        records = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise InvalidRepositoryUrlError(f"Unable to resolve {host}") from exc
    for record in records:
        address = record[4][0]
        if not ipaddress.ip_address(address).is_global:
            raise InvalidRepositoryUrlError(f"{host} resolved to a non-public address")


async def download_github_archive(
    owner: str,
    repo: str,
    branch: str | None,
    destination: Path,
    max_bytes: int,
) -> str:
    """Stream a GitHub repository's zip archive to ``destination``.

    Returns the branch name that was actually downloaded. If ``branch`` is
    omitted, tries ``main`` then ``master`` (GitHub's two common defaults —
    the codeload endpoint has no "give me the default branch" shortcut
    without an extra API call).
    """
    _assert_resolves_public(_CODELOAD_HOST)
    candidates = [branch] if branch else ["main", "master"]
    last_error: InvalidRepositoryUrlError | None = None
    timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for candidate in candidates:
            archive_url = f"https://{_CODELOAD_HOST}/{owner}/{repo}/zip/refs/heads/{candidate}"
            try:
                async with client.stream("GET", archive_url, follow_redirects=True) as response:
                    if response.status_code == 404:
                        last_error = InvalidRepositoryUrlError(
                            f"Branch '{candidate}' not found for {owner}/{repo}"
                        )
                        continue
                    response.raise_for_status()
                    if response.url.host not in {_CODELOAD_HOST, _GITHUB_HOST}:
                        raise InvalidRepositoryUrlError(
                            "Unexpected redirect target while downloading archive"
                        )
                    written = 0
                    with destination.open("wb") as handle:
                        async for chunk in response.aiter_bytes(1024 * 1024):
                            written += len(chunk)
                            if written > max_bytes:
                                raise InvalidRepositoryUrlError(
                                    f"Repository archive exceeds {max_bytes // (1024 * 1024)} MiB"
                                )
                            handle.write(chunk)
                    return candidate
            except httpx.HTTPError as exc:
                last_error = InvalidRepositoryUrlError(
                    f"Could not download repository archive: {exc}"
                )
                continue
    raise last_error or InvalidRepositoryUrlError("Could not download repository archive")
