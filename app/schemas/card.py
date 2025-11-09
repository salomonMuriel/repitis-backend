"""Card response schemas."""

from typing import Literal

from pydantic import BaseModel


class CardResponse(BaseModel):
    """
    Card data response schema.

    Exposes only necessary card fields to clients (security boundary).
    """

    id: str
    content: str
    content_type: Literal["letter", "syllable", "word"]
    image_url: str | None
    audio_url: str | None
    level_id: int
    is_new: bool


class NextCardResponse(BaseModel):
    """
    Next card response schema.

    Returns the next card to review, or None if session is complete.
    """

    card: CardResponse | None
    session_complete: bool
    message: str | None = None
