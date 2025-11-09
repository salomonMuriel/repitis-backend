"""Card selection and review business logic."""

import logging
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, func, select

from app.config import settings
from app.models import Card, CardProgress, Level, Profile, ReviewLog
from app.services.fsrs import FSRSService

logger = logging.getLogger(__name__)


class CardService:
    """Service for card selection and review processing."""

    def __init__(self) -> None:
        """Initialize card service with FSRS service."""
        self.fsrs_service = FSRSService()

    def get_next_card(self, session: Session, user_id: str) -> tuple[Card | None, bool]:
        """
        Get the next card for user to review based on FSRS algorithm.

        Selection algorithm:
        1. Check daily review limit (total reviews today)
        2. Prioritize due cards (next_review <= now)
        3. If no due cards, select new card from current level or below
        4. Enforce daily new card limit
        5. Return None if session complete

        Args:
            session: Database session
            user_id: User ID

        Returns:
            tuple[Card | None, bool]: Next card to review (or None) and whether it's new
        """
        now = datetime.now(timezone.utc)

        # Step 1: Check daily review limit
        if not self._can_review(session, user_id, now):
            logger.debug("Daily review limit reached, session complete")
            return None, False

        # Step 2: Check for due cards
        due_card = self._get_due_card(session, user_id, now)
        if due_card:
            logger.debug(f"Selected due card: {due_card.id}")
            return due_card, False

        # Step 3: Check daily new card limit
        if not self._can_get_new_card(session, user_id, now):
            logger.debug("Daily new card limit reached, session complete")
            return None, False

        # Step 4: Get new card from current level or below
        new_card = self._get_new_card(session, user_id)
        if new_card:
            logger.debug(f"Selected new card: {new_card.id}")
            return new_card, True
        else:
            logger.debug("No new cards available, session complete")
            return None, False

    def submit_review(
        self, session: Session, user_id: str, card_id: str, rating: int
    ) -> datetime:
        """
        Submit a card review and update FSRS state.

        Args:
            session: Database session
            user_id: User ID
            card_id: Card ID
            rating: Review rating (1=Again, 2=Hard, 3=Good, 4=Easy)

        Returns:
            datetime: Next review timestamp

        Raises:
            ValueError: If card progress not found or rating invalid
        """
        # Get or create card progress
        progress = session.get(CardProgress, (user_id, card_id))

        if progress is None:
            # Create new progress for first review
            fsrs_state = self.fsrs_service.create_new_card(card_id=card_id)
            progress = CardProgress(
                user_id=user_id,
                card_id=card_id,
                fsrs_state=fsrs_state,  # Already clean dict from to_dict()
                next_review=datetime.now(timezone.utc),
            )
            session.add(progress)
            logger.debug(f"Created new progress for card {card_id}")

        # Process review with FSRS (normalize datetime fields for Card.from_dict())
        updated_state, next_review, fsrs_review_log = self.fsrs_service.review_card(
            progress.fsrs_state, rating
        )

        # Update progress (to_dict() already returns clean dict)
        progress.fsrs_state = updated_state
        progress.next_review = next_review
        progress.last_review = datetime.now(timezone.utc)

        # Track highest stability ever achieved and mastered_at timestamp
        current_stability = updated_state.get('stability', 0.0)
        if current_stability > progress.highest_stability:
            progress.highest_stability = current_stability
            # Mark as mastered when first reaching 7+ days stability
            if current_stability >= 7.0 and progress.mastered_at is None:
                progress.mastered_at = datetime.now(timezone.utc)
                logger.info(f"Card {card_id} mastered by user {user_id} (stability: {current_stability:.1f} days)")

        # Insert immutable review log with FSRS ReviewLog data
        review_log = ReviewLog(
            user_id=user_id,
            card_id=card_id,
            rating=rating,
            reviewed_at=datetime.now(timezone.utc),
            fsrs_data=fsrs_review_log,  # Store FSRS ReviewLog.to_dict()
        )
        session.add(review_log)

        # Check for level progression (before commit)
        self._check_and_promote_level(session, user_id)

        session.commit()

        logger.info(
            f"Review submitted: user={user_id}, card={card_id}, rating={rating}, next={next_review}"
        )

        return next_review

    def _get_due_card(
        self, session: Session, user_id: str, now: datetime
    ) -> Card | None:
        """Get the most urgent due card (next_review <= now)."""
        statement = (
            select(Card)
            .join(CardProgress, CardProgress.card_id == Card.id)
            .where(CardProgress.user_id == user_id)
            .where(CardProgress.next_review <= now)
            .order_by(CardProgress.next_review.asc())
            .limit(1)
        )
        return session.exec(statement).first()

    def _get_new_card(self, session: Session, user_id: str) -> Card | None:
        """Get a new card from current level or below."""
        # Get user's current level
        profile = session.get(Profile, user_id)
        if not profile:
            logger.error(f"Profile not found for user {user_id}")
            return None

        # Get cards from current level or below that user hasn't started
        statement = (
            select(Card)
            .where(Card.level_id <= profile.current_level)
            .where(
                ~Card.id.in_(
                    select(CardProgress.card_id).where(
                        CardProgress.user_id == user_id
                    )
                )
            )
            .order_by(Card.level_id.asc(), Card.id.asc())
            .limit(1)
        )
        return session.exec(statement).first()

    def _can_review(
        self, session: Session, user_id: str, now: datetime
    ) -> bool:
        """Check if user can do another review (daily total limit check)."""
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Count total reviews today
        statement = (
            select(func.count())
            .select_from(ReviewLog)
            .where(ReviewLog.user_id == user_id)
            .where(ReviewLog.reviewed_at >= today_start)
        )
        reviews_today = session.exec(statement).one()

        can_review = reviews_today < settings.max_reviews_per_day
        logger.debug(
            f"Reviews today: {reviews_today}/{settings.max_reviews_per_day}"
        )

        return can_review

    def _can_get_new_card(
        self, session: Session, user_id: str, now: datetime
    ) -> bool:
        """Check if user can get a new card (daily limit check)."""
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Count new cards reviewed today
        statement = (
            select(func.count())
            .select_from(CardProgress)
            .where(CardProgress.user_id == user_id)
            .where(CardProgress.created_at >= today_start)
        )
        new_cards_today = session.exec(statement).one()

        can_get = new_cards_today < settings.max_new_cards_per_day
        logger.debug(
            f"New cards today: {new_cards_today}/{settings.max_new_cards_per_day}"
        )

        return can_get

    def _check_and_promote_level(self, session: Session, user_id: str) -> bool:
        """
        Check if user has mastered current level and promote if eligible.

        Called after each review to check if the user has reached the mastery
        threshold for their current level. If so, promotes them to the next level.

        A card is considered "mastered" when it has ever achieved 7+ days stability
        (tracked via highest_stability field). This is permanent - once mastered,
        always mastered, preventing level regression.

        Args:
            session: Database session
            user_id: User ID

        Returns:
            bool: True if user was promoted, False otherwise
        """
        # Get user profile
        profile = session.get(Profile, user_id)
        if not profile:
            logger.error(f"Profile not found for user {user_id}")
            return False

        # Don't check if already at max level
        if profile.current_level >= 10:
            return False

        current_level_id = profile.current_level

        # Get level configuration
        level = session.get(Level, current_level_id)
        if not level:
            logger.error(f"Level {current_level_id} not found")
            return False

        # Count total cards in current level
        total_cards = session.exec(
            select(func.count())
            .select_from(Card)
            .where(Card.level_id == current_level_id)
        ).one()

        if total_cards == 0:
            logger.warning(f"No cards found for level {current_level_id}")
            return False

        # Count mastered cards (highest_stability >= 7 days, permanent)
        mastered_cards = session.exec(
            select(func.count())
            .select_from(CardProgress)
            .join(Card, Card.id == CardProgress.card_id)
            .where(CardProgress.user_id == user_id)
            .where(Card.level_id == current_level_id)
            .where(CardProgress.highest_stability >= 7.0)
        ).one()

        progress_percentage = mastered_cards / total_cards

        # Check if mastery threshold reached
        if progress_percentage >= level.mastery_threshold:
            old_level = profile.current_level
            profile.current_level += 1
            profile.updated_at = datetime.now(timezone.utc)

            logger.info(
                f"Level promotion: user={user_id}, level {old_level} -> {profile.current_level}, "
                f"progress={progress_percentage:.1%} (mastered {mastered_cards}/{total_cards} cards)"
            )
            return True

        logger.debug(
            f"Level {current_level_id} progress: {progress_percentage:.1%} "
            f"({mastered_cards}/{total_cards} mastered, threshold={level.mastery_threshold:.1%})"
        )
        return False
