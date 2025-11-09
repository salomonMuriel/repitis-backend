"""Levels API routes."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlmodel import func, select

from app.auth import CurrentUser
from app.database import SessionDep
from app.models import Card, CardProgress, Level, Profile
from app.schemas import LevelResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/levels", tags=["levels"])


@router.get("", response_model=list[LevelResponse])
async def get_levels(session: SessionDep, user_id: CurrentUser) -> list[LevelResponse]:
    """
    Get all levels with user progress.

    Returns all 10 levels with unlock status and progress percentages.

    Args:
        session: Database session (injected)
        user_id: Authenticated user ID (injected)

    Returns:
        list[LevelResponse]: All levels with progress data

    Raises:
        HTTPException: 404 if user not found, 500 on other errors
    """
    logger.info(f"Fetching levels for user {user_id}")

    try:
        # Get user profile
        profile = session.get(Profile, user_id)
        if not profile:
            raise ValueError(f"Profile not found for user {user_id}")

        # Get all levels
        levels = session.exec(select(Level).order_by(Level.id)).all()

        response = []
        for level in levels:
            # Calculate progress
            total_cards = session.exec(
                select(func.count())
                .select_from(Card)
                .where(Card.level_id == level.id)
            ).one()

            # Count mastered cards (next_review > 7 days from now)
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

            # Level is unlocked if it's the current level or below
            is_unlocked = level.id <= profile.current_level

            response.append(
                LevelResponse(
                    id=level.id,
                    name=level.name,
                    description=level.description,
                    mastery_threshold=level.mastery_threshold,
                    is_unlocked=is_unlocked,
                    progress_percentage=round(progress_percentage, 1),
                )
            )

        return response

    except ValueError as e:
        logger.warning(f"User not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error fetching levels: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch levels",
        ) from e
