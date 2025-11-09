"""ReviewLog model - Immutable review history."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class ReviewLog(SQLModel, table=True):
    """
    Review log table.

    Immutable record of all card reviews for statistics and analytics.
    Insert-only, never updated or deleted.

    Stores FSRS ReviewLog data in fsrs_data JSONB column:
    - card_id: FSRS internal card ID
    - rating: Review rating
    - review_datetime: Review timestamp
    - review_duration: Duration in milliseconds (if tracked)
    """

    __tablename__ = "review_logs"

    id: int | None = Field(default=None, primary_key=True, description="Auto-incrementing log ID")
    user_id: UUID = Field(foreign_key="profiles.id", index=True, description="User ID (UUID)")
    card_id: str = Field(foreign_key="cards.id", index=True, description="Card ID")
    rating: int = Field(ge=1, le=4, description="Review rating (1=Again, 2=Hard, 3=Good, 4=Easy)")
    reviewed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
        description="Review timestamp (indexed for queries)",
    )

    # FSRS ReviewLog data (from py-fsrs ReviewLog.to_dict())
    fsrs_data: dict | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="FSRS ReviewLog data as JSONB"
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<ReviewLog(id={self.id}, user={self.user_id!r}, rating={self.rating}, at={self.reviewed_at})>"
