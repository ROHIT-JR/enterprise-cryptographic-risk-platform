from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.asset import Asset


class RiskFinding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_findings"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    factors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    asset: Mapped["Asset"] = relationship(back_populates="risk")
