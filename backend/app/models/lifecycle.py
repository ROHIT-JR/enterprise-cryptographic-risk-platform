from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.asset import Asset


class CryptoLifecycleEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crypto_lifecycle_events"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_state: Mapped[str | None] = mapped_column(String(32), index=True)
    new_state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    previous_governance_status: Mapped[str | None] = mapped_column(String(32), index=True)
    new_governance_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(1024))
    actor_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    actor_role: Mapped[str | None] = mapped_column(String(32))
    related_risk_analysis_id: Mapped[str | None] = mapped_column(String(36), index=True)
    related_plan_id: Mapped[str | None] = mapped_column(String(36), index=True)
    migration_wave: Mapped[int | None] = mapped_column(Integer, index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    engine_version: Mapped[str | None] = mapped_column(String(32))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )

    asset: Mapped["Asset"] = relationship(back_populates="lifecycle_events")
