"""Level model - Reading difficulty levels."""

from sqlmodel import Field, SQLModel


class Level(SQLModel, table=True):
    """
    Reading difficulty level table.

    Defines the 10 progressive difficulty levels from vowels to complex patterns.
    """

    __tablename__ = "levels"

    id: int = Field(primary_key=True, ge=1, le=10, description="Level number (1-10)")
    name: str = Field(max_length=100, description="Level name (e.g., 'Vowels', 'Syllables')")
    description: str = Field(max_length=500, description="Level description")
    mastery_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Percentage of cards to master before unlocking (0.0-1.0)",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Level(id={self.id}, name={self.name!r})>"
