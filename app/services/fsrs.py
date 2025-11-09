"""FSRS (Free Spaced Repetition Scheduler) service wrapper."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fsrs import Card, Rating, Scheduler

from app.config import settings

logger = logging.getLogger(__name__)


class FSRSService:
    """
    Thin wrapper around py-fsrs library for spaced repetition scheduling.

    Provides methods to create new cards and process reviews with proper FSRS algorithm.
    """

    def __init__(self) -> None:
        """Initialize FSRS scheduler with configured parameters."""
        # Convert learning steps from minutes (int list) to timedelta tuple
        learning_steps = tuple(timedelta(minutes=m) for m in settings.learning_steps_list)

        self.scheduler = Scheduler(
            desired_retention=settings.fsrs_desired_retention,
            learning_steps=learning_steps,
            maximum_interval=settings.fsrs_maximum_interval,
        )
        logger.info(
            f"FSRS scheduler initialized: retention={settings.fsrs_desired_retention}, "
            f"steps={learning_steps}, max_interval={settings.fsrs_maximum_interval}"
        )

    def create_new_card(self, card_id: str | None = None) -> dict:
        """
        Create initial FSRS state for a new card.

        Args:
            card_id: Optional card identifier (for logging only, not stored in FSRS state)

        Returns:
            dict: FSRS card state serialized to dictionary (JSONB-compatible)

        Example:
            ```python
            fsrs_service = FSRSService()
            initial_state = fsrs_service.create_new_card(card_id="vowel_a_lower")
            # Store initial_state in card_progress.fsrs_state (JSONB)
            ```
        """
        # Note: py-fsrs Card expects card_id to be int | None, but we use string IDs.
        # Since we track card_id in CardProgress table, we don't need it in FSRS state.
        card = Card()
        logger.debug(f"Created new FSRS card state for card_id={card_id}")
        return card.to_dict()

    def review_card(self, fsrs_state: dict, rating: int) -> tuple[dict, datetime, dict]:
        """
        Process a card review and return updated FSRS state.

        Args:
            fsrs_state: Current FSRS card state (from card_progress.fsrs_state)
            rating: Review rating (1=Again, 2=Hard, 3=Good, 4=Easy)

        Returns:
            tuple[dict, datetime, dict]: (updated_fsrs_state, next_review_datetime, review_log_dict)
                review_log_dict: FSRS ReviewLog.to_dict() for storage

        Raises:
            ValueError: If rating is not in range 1-4

        Example:
            ```python
            fsrs_service = FSRSService()
            current_state = {"stability": 1.0, "difficulty": 5.0, ...}
            updated_state, next_review, review_log = fsrs_service.review_card(current_state, 3)
            # Store updated_state in card_progress.fsrs_state
            # Store next_review in card_progress.next_review
            # Store review_log in review_logs.fsrs_data
            ```
        """
        if rating not in (1, 2, 3, 4):
            raise ValueError(f"Invalid rating: {rating}. Must be 1-4.")

        # Normalize datetime fields for Card.from_dict()
        normalized_state = self._normalize_fsrs_state(fsrs_state)
        card = Card.from_dict(normalized_state)

        # Convert rating to enum
        rating_enum = Rating(rating)

        # Process review with FSRS algorithm (use timezone-aware datetime)
        review_time = datetime.now(timezone.utc)
        card, review_log = self.scheduler.review_card(
            card, rating_enum, review_datetime=review_time
        )

        # Return updated state, next review time, and FSRS ReviewLog
        updated_state = card.to_dict()
        next_review = card.due
        review_log_dict = review_log.to_dict()

        logger.debug(
            f"Processed review: rating={rating_enum.name}, next_review={next_review}"
        )

        return updated_state, next_review, review_log_dict

    def _normalize_fsrs_state(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize FSRS state for Card.from_dict().

        The FSRS library's Card.from_dict() expects datetime fields as ISO strings.
        SQLAlchemy may return them as either strings (from JSONB) or datetime objects
        (from in-memory objects). This method ensures they're always strings.

        Note: We don't touch the card_id field - FSRS manages its own internal card_id,
        and we track our application card IDs separately in CardProgress.card_id.

        Args:
            state: FSRS state dict from database

        Returns:
            dict: Normalized state with datetime fields as ISO strings
        """
        normalized = state.copy()

        # Convert datetime objects to ISO strings (Card.from_dict expects strings)
        if "due" in normalized and normalized["due"] is not None:
            if isinstance(normalized["due"], datetime):
                normalized["due"] = normalized["due"].isoformat()
            # If it's already a string, leave it as is

        if "last_review" in normalized and normalized["last_review"] is not None:
            if isinstance(normalized["last_review"], datetime):
                normalized["last_review"] = normalized["last_review"].isoformat()
            # If it's already a string, leave it as is

        return normalized
