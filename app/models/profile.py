"""Profile model - User data."""

from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Field, SQLModel


class Profile(SQLModel, table=True):
    """
    User profile table.

    Stores basic user information and current learning level.
    Automatically created via trigger when user signs up via Supabase Auth.
    """

    __tablename__ = "profiles"

    id: UUID = Field(primary_key=True, description="Supabase Auth user ID (UUID)")
    name: str = Field(max_length=255, description="User's display name")
    current_level: int = Field(default=1, ge=1, le=10, description="Current learning level (1-10)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Account creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")

    def __repr__(self) -> str:
        """String representation."""
        return f"<Profile(id={self.id!r}, name={self.name!r}, level={self.current_level})>"
