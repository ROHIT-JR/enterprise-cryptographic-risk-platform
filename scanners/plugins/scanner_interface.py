from pydantic import BaseModel

from scanners.base import ScannerPlugin


class ScannerMetadata(BaseModel):
    name: str
    version: str
    source_type: str


class Scanner(ScannerPlugin):
    """Stable public interface for built-in and third-party ECDAT-X scanners."""

    @property
    def metadata(self) -> ScannerMetadata:
        return ScannerMetadata(
            name=self.name,
            version=self.version,
            source_type=str(self.source_type),
        )
