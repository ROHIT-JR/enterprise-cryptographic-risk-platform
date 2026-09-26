from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from local names and ECDAT_* aliases."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ECDAT_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ECDAT-X API"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    database_url: str = Field(
        default="sqlite+pysqlite:///./ecdat.db",
        validation_alias=AliasChoices("ECDAT_DATABASE_URL", "DATABASE_URL"),
    )
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    scan_storage_path: Path = Path("./scan-data")
    max_upload_bytes: int = 50 * 1024 * 1024
    max_archive_files: int = 20_000
    max_archive_uncompressed_bytes: int = 250 * 1024 * 1024
    scanner_timeout_seconds: int = 45
    tls_connect_timeout_seconds: float = 8.0
    tls_allow_private_targets: bool = False
    docker_enabled: bool = True
    enable_scanner_discovery: bool = False
    neo4j_enabled: bool = True
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        validation_alias=AliasChoices("ECDAT_NEO4J_URI", "NEO4J_URI"),
    )
    neo4j_user: str = Field(
        default="neo4j",
        validation_alias=AliasChoices("ECDAT_NEO4J_USER", "NEO4J_USERNAME", "NEO4J_USER"),
    )
    neo4j_password: str = Field(
        default="",
        validation_alias=AliasChoices("ECDAT_NEO4J_PASSWORD", "NEO4J_PASSWORD"),
    )
    seed_demo: bool = False
    admin_username: str | None = None
    admin_password: str | None = None
    secret_key: str = "development-only-not-used-for-authentication"
    jwt_issuer: str = "ecdat-x"
    jwt_audience: str = "ecdat-x-api"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    rate_limit_per_minute: int = 120
    demo_password: str = "SecureBank-Demo-2026"
    log_level: str = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("scan_storage_path", mode="before")
    @classmethod
    def expand_storage_path(cls, value: object) -> Path:
        return Path(str(value)).expanduser()


@lru_cache
def get_settings() -> Settings:
    return Settings()
