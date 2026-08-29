from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.asset import Asset


class BusinessContext(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "business_context"

    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    criticality: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    owner: Mapped[str | None] = mapped_column(String(160))
    data_lifetime_years: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    data_sensitivity: Mapped[str] = mapped_column(String(32), default="internal", nullable=False)
    downtime_requirement: Mapped[str] = mapped_column(
        String(32), default="standard", nullable=False
    )
    compatibility: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    legacy_technology: Mapped[bool] = mapped_column(default=False, nullable=False)

    asset: Mapped["Asset"] = relationship(back_populates="business_context")
