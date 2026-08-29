from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.asset import Asset


class RiskAnalysis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_analysis"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    quantum_score: Mapped[float] = mapped_column(Float, nullable=False)
    hndl_score: Mapped[float] = mapped_column(Float, nullable=False)
    centrality_score: Mapped[float] = mapped_column(Float, nullable=False)
    business_score: Mapped[float] = mapped_column(Float, nullable=False)
    migration_complexity_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    final_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    hndl_risk: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    quantum_classification: Mapped[str] = mapped_column(String(16), nullable=False)
    dependent_systems: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evidence_sources: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    explanations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    factors: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    asset: Mapped["Asset"] = relationship(back_populates="intelligence")


class MigrationPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "migration_plan"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    recommended_algorithm: Mapped[str] = mapped_column(String(255), nullable=False)
    wave: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    complexity: Mapped[str] = mapped_column(String(16), nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    recommendation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    asset: Mapped["Asset"] = relationship(back_populates="migration_plan")
