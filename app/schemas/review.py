"""Review request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    """
    Review submission request schema.

    Client submits rating for a card review.
    """

    rating: int = Field(ge=1, le=4, description="Review rating (1=Again, 2=Hard, 3=Good, 4=Easy)")


class ReviewResponse(BaseModel):
    """
    Review submission response schema.

    Confirms review was processed and provides next review timestamp.
    """

    success: bool
    next_review: datetime
    message: str = "Review submitted successfully"
