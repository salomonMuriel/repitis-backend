"""CardProgress model - User-specific FSRS state."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class CardProgress(SQLModel, table=True):
    """
    Card progress table.

    Stores user-specific FSRS state for each card using JSONB.
    Composite primary key: (user_id, card_id)
    """

    __tablename__ = "card_progress"

    user_id: UUID = Field(foreign_key="profiles.id", primary_key=True, description="User ID (UUID)")
    card_id: str = Field(foreign_key="cards.id", primary_key=True, description="Card ID")
    fsrs_state: dict = Field(sa_column=Column(JSONB), description="FSRS algorithm state as JSONB")
    next_review: datetime = Field(description="Next scheduled review timestamp")
    last_review: datetime | None = Field(default=None, description="Last review timestamp")
    highest_stability: float = Field(default=0.0, description="Highest stability (days) ever achieved for this card")
    mastered_at: datetime | None = Field(default=None, description="Timestamp when card first reached 7+ days stability (permanent)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="First learning timestamp")

    def __repr__(self) -> str:
        """String representation."""
        return f"<CardProgress(user={self.user_id!r}, card={self.card_id!r}, next={self.next_review})>"
