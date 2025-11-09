"""Card model - Learning cards."""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class Card(SQLModel, table=True):
    """
    Learning card table.

    Stores individual learning items (letters, syllables, words) with media references.
    """

    __tablename__ = "cards"

    id: str = Field(primary_key=True, description="Unique card identifier")
    level_id: int = Field(foreign_key="levels.id", description="Associated level (1-10)")
    content: str = Field(max_length=100, description="Card text content (letter, syllable, word)")
    content_type: str = Field(max_length=20, description="Type of content (letter, syllable, word)")
    image_url: str | None = Field(default=None, max_length=500, description="Path to illustration image")
    audio_url: str | None = Field(default=None, max_length=500, description="Path to pronunciation audio")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Card creation timestamp")

    def __repr__(self) -> str:
        """String representation."""
        return f"<Card(id={self.id!r}, content={self.content!r}, type={self.content_type})>"
