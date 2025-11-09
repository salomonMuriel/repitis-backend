"""Level response schemas."""

from pydantic import BaseModel


class LevelResponse(BaseModel):
    """
    Level data response schema.

    Exposes level information with user progress.
    """

    id: int
    name: str
    description: str
    mastery_threshold: float
    is_unlocked: bool
    progress_percentage: float
