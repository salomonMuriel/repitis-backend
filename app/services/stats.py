"""Statistics calculation service."""

import logging
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, func, select

from app.models import Card, CardProgress, Level, Profile, ReviewLog
from app.schemas import LevelProgress, StatsResponse, TodayStatsResponse

logger = logging.getLogger(__name__)


class StatsService:
    """Service for calculating user statistics on-demand."""

    @staticmethod
    def get_user_stats(session: Session, user_id: str) -> StatsResponse:
        """
        Calculate and return all user statistics.

        Calculates on-demand from review_logs and card_progress tables.

        Args:
            session: Database session
            user_id: User ID

        Returns:
            StatsResponse: Aggregated user statistics
        """
        profile = session.get(Profile, user_id)
        if not profile:
            raise ValueError(f"Profile not found for user {user_id}")

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Count today's reviews
        today_reviews = StatsService._count_reviews_since(session, user_id, today_start)

        # Count total reviews
        total_reviews = StatsService._count_total_reviews(session, user_id)

        # Calculate streak
        current_streak = StatsService._calculate_current_streak(session, user_id, now)
        longest_streak = StatsService._calculate_longest_streak(session, user_id)

        # Get level progress
        level_progress = StatsService._get_level_progress(session, user_id)

        logger.debug(
            f"Stats for user {user_id}: today={today_reviews}, total={total_reviews}, streak={current_streak}"
        )

        return StatsResponse(
            today_reviews=today_reviews,
            total_reviews=total_reviews,
            current_streak=current_streak,
            longest_streak=longest_streak,
            level_progress=level_progress,
            current_level=profile.current_level,
        )

    @staticmethod
    def get_today_stats(session: Session, user_id: str) -> TodayStatsResponse:
        """
        Get today's review statistics (lightweight endpoint for review sessions).

        Args:
            session: Database session
            user_id: User ID

        Returns:
            TodayStatsResponse: New cards and total reviews for today
        """
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Count total reviews today
        total_reviews_today = StatsService._count_reviews_since(session, user_id, today_start)

        # Count new cards today (cards reviewed for the first time today)
        new_cards_today = session.exec(
            select(func.count())
            .select_from(CardProgress)
            .where(CardProgress.user_id == user_id)
            .where(CardProgress.created_at >= today_start)
        ).one()

        logger.debug(
            f"Today's stats for user {user_id}: new={new_cards_today}, total={total_reviews_today}"
        )

        return TodayStatsResponse(
            new_cards_today=new_cards_today,
            total_reviews_today=total_reviews_today,
        )

    @staticmethod
    def _count_reviews_since(session: Session, user_id: str, since: datetime) -> int:
        """Count reviews since a given timestamp."""
        statement = (
            select(func.count())
            .select_from(ReviewLog)
            .where(ReviewLog.user_id == user_id)
            .where(ReviewLog.reviewed_at >= since)
        )
        return session.exec(statement).one()

    @staticmethod
    def _count_total_reviews(session: Session, user_id: str) -> int:
        """Count all reviews for user."""
        statement = (
            select(func.count())
            .select_from(ReviewLog)
            .where(ReviewLog.user_id == user_id)
        )
        return session.exec(statement).one()

    @staticmethod
    def _calculate_current_streak(session: Session, user_id: str, now: datetime) -> int:
        """
        Calculate current consecutive days with reviews.

        Returns:
            int: Number of consecutive days with at least one review
        """
        streak = 0
        check_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

        while True:
            next_day = check_date + timedelta(days=1)

            # Count reviews on this specific day (between check_date and next_day)
            statement = (
                select(func.count())
                .select_from(ReviewLog)
                .where(ReviewLog.user_id == user_id)
                .where(ReviewLog.reviewed_at >= check_date)
                .where(ReviewLog.reviewed_at < next_day)
            )
            count = session.exec(statement).one()

            if count == 0:
                break

            streak += 1
            check_date -= timedelta(days=1)

            # Limit to prevent infinite loop (reasonable max)
            if streak > 1000:
                break

        return streak

    @staticmethod
    def _calculate_longest_streak(session: Session, user_id: str) -> int:
        """
        Calculate longest historical streak.

        For MVP, return current streak. Can be enhanced later with more complex logic.

        Returns:
            int: Longest streak in days
        """
        # For MVP, longest = current (simplified)
        # TODO: Implement full historical streak calculation if needed
        return StatsService._calculate_current_streak(
            session, user_id, datetime.now(timezone.utc)
        )

    @staticmethod
    def _get_level_progress(session: Session, user_id: str) -> list[LevelProgress]:
        """
        Calculate progress for each level.

        Returns:
            list[LevelProgress]: Progress data for all 10 levels
        """
        levels = session.exec(select(Level).order_by(Level.id)).all()
        progress_list = []

        for level in levels:
            # Count total cards in level
            total_cards = session.exec(
                select(func.count())
                .select_from(Card)
                .where(Card.level_id == level.id)
            ).one()

            # Count mastered cards (arbitrary threshold: reviewed 3+ times with Good/Easy)
            # For MVP, use simplified logic: cards with stability > 7 days
            mastered_cards = session.exec(
                select(func.count())
                .select_from(CardProgress)
                .join(Card, Card.id == CardProgress.card_id)
                .where(CardProgress.user_id == user_id)
                .where(Card.level_id == level.id)
                .where(CardProgress.next_review > datetime.now(timezone.utc) + timedelta(days=7))
            ).one()

            progress_percentage = (
                (mastered_cards / total_cards * 100) if total_cards > 0 else 0.0
            )

            progress_list.append(
                LevelProgress(
                    level_id=level.id,
                    level_name=level.name,
                    total_cards=total_cards,
                    mastered_cards=mastered_cards,
                    progress_percentage=round(progress_percentage, 1),
                )
            )

        return progress_list
