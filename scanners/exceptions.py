class ScannerError(RuntimeError):
    """Base exception for a scanner failure safe to surface to an analyst."""


class ScannerUnavailableError(ScannerError):
    """Raised when a scanner dependency is unavailable."""


class InvalidScanTargetError(ScannerError):
    """Raised when a supplied target fails validation."""


class UnsafeArchiveError(ScannerError):
    """Raised when an uploaded archive violates extraction safety limits."""
