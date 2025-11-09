"""Statistics response schemas."""

from pydantic import BaseModel


class LevelProgress(BaseModel):
    """Progress for a single level."""

    level_id: int
    level_name: str
    total_cards: int
    mastered_cards: int
    progress_percentage: float


class StatsResponse(BaseModel):
    """
    User statistics response schema.

    Aggregated user learning statistics calculated on-demand.
    """

    today_reviews: int
    total_reviews: int
    current_streak: int
    longest_streak: int
    level_progress: list[LevelProgress]
    current_level: int


class TodayStatsResponse(BaseModel):
    """
    Today's review statistics response schema.

    Lightweight endpoint for real-time review session tracking.
    """

    new_cards_today: int
    total_reviews_today: int
