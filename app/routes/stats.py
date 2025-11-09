"""Statistics API routes."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.auth import CurrentUser
from app.database import SessionDep
from app.schemas import StatsResponse, TodayStatsResponse
from app.services import StatsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
async def get_user_stats(session: SessionDep, user_id: CurrentUser) -> StatsResponse:
    """
    Get user statistics.

    Returns all user statistics calculated on-demand from review logs.

    Args:
        session: Database session (injected)
        user_id: Authenticated user ID (injected)

    Returns:
        StatsResponse: User statistics including reviews, streaks, and level progress

    Raises:
        HTTPException: 404 if user not found, 500 on other errors
    """
    logger.info(f"Fetching stats for user {user_id}")

    try:
        stats = StatsService.get_user_stats(session, user_id)
        return stats

    except ValueError as e:
        logger.warning(f"User not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error fetching stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch statistics",
        ) from e


@router.get("/today", response_model=TodayStatsResponse)
async def get_today_stats(session: SessionDep, user_id: CurrentUser) -> TodayStatsResponse:
    """
    Get today's review statistics.

    Lightweight endpoint for real-time tracking during review sessions.
    Returns new cards and total reviews for today.

    Args:
        session: Database session (injected)
        user_id: Authenticated user ID (injected)

    Returns:
        TodayStatsResponse: Today's new cards and total reviews counts

    Raises:
        HTTPException: 500 on errors
    """
    logger.info(f"Fetching today's stats for user {user_id}")

    try:
        stats = StatsService.get_today_stats(session, user_id)
        return stats

    except Exception as e:
        logger.error(f"Error fetching today's stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch today's statistics",
        ) from e
