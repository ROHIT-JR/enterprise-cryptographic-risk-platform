from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.business import BusinessContext
    from backend.app.models.intelligence import MigrationPlan, RiskAnalysis
    from backend.app.models.lifecycle import CryptoLifecycleEvent
    from backend.app.models.project import Project
    from backend.app.models.risk import RiskFinding
    from backend.app.models.scan import Scan


class Asset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint(
            "scan_id", "asset_type", "name", "location", "evidence", name="uq_scan_asset_evidence"
        ),
    )

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scan_id: Mapped[str] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    algorithm: Mapped[str | None] = mapped_column(String(120), index=True)
    version: Mapped[str | None] = mapped_column(String(120))
    location: Mapped[str] = mapped_column(String(1024), nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    dependency_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    
    # Lifecycle Tracking
    lifecycle_state: Mapped[str] = mapped_column(
        String(32), default="DISCOVERED", nullable=False, index=True
    )
    governance_status: Mapped[str] = mapped_column(
        String(32), default="ACTIVE", nullable=False, index=True
    )
    lifecycle_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="assets")
    scan: Mapped["Scan"] = relationship(back_populates="assets")
    risk: Mapped["RiskFinding | None"] = relationship(
        back_populates="asset", cascade="all, delete-orphan", uselist=False
    )
    business_context: Mapped["BusinessContext | None"] = relationship(
        back_populates="asset", cascade="all, delete-orphan", uselist=False
    )
    intelligence: Mapped["RiskAnalysis | None"] = relationship(
        back_populates="asset", cascade="all, delete-orphan", uselist=False
    )
    migration_plan: Mapped["MigrationPlan | None"] = relationship(
        back_populates="asset", cascade="all, delete-orphan", uselist=False
    )
    lifecycle_events: Mapped[list["CryptoLifecycleEvent"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )


class AssetRelationship(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "asset_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_asset_id",
            "target_asset_id",
            "relationship_type",
            name="uq_asset_relationship",
        ),
    )

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text)
