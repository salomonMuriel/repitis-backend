"""Card-related API routes."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.auth import CurrentUser
from app.database import SessionDep
from app.schemas import CardResponse, NextCardResponse, ReviewRequest, ReviewResponse
from app.services import CardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cards", tags=["cards"])
card_service = CardService()


@router.get("/next", response_model=NextCardResponse)
async def get_next_card(session: SessionDep, user_id: CurrentUser) -> NextCardResponse:
    """
    Get the next card to review.

    Returns the next due card or a new card based on FSRS algorithm.
    Returns null if session is complete (no due cards + daily limit reached).

    Args:
        session: Database session (injected)
        user_id: Authenticated user ID (injected)

    Returns:
        NextCardResponse: Next card or session complete message
    """
    logger.info(f"Fetching next card for user {user_id}")

    try:
        card, is_new = card_service.get_next_card(session, user_id)

        if card is None:
            return NextCardResponse(
                card=None,
                session_complete=True,
                message="Great job! You've completed today's reviews.",
            )

        card_response = CardResponse(
            id=card.id,
            content=card.content,
            content_type=card.content_type,
            image_url=card.image_url,
            audio_url=card.audio_url,
            level_id=card.level_id,
            is_new=is_new,
        )

        return NextCardResponse(
            card=card_response,
            session_complete=False,
            message=None,
        )

    except Exception as e:
        logger.error(f"Error fetching next card: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch next card",
        ) from e


@router.post("/{card_id}/review", response_model=ReviewResponse)
async def submit_review(
    card_id: str,
    review: ReviewRequest,
    session: SessionDep,
    user_id: CurrentUser,
) -> ReviewResponse:
    """
    Submit a card review.

    Processes the review with FSRS algorithm and updates card progress.

    Args:
        card_id: Card ID to review
        review: Review data with rating (1-4)
        session: Database session (injected)
        user_id: Authenticated user ID (injected)

    Returns:
        ReviewResponse: Confirmation with next review timestamp

    Raises:
        HTTPException: 400 if rating invalid, 404 if card not found
    """
    logger.info(f"User {user_id} reviewing card {card_id} with rating {review.rating}")

    try:
        next_review = card_service.submit_review(
            session, user_id, card_id, review.rating
        )

        return ReviewResponse(
            success=True,
            next_review=next_review,
            message="Review submitted successfully",
        )

    except ValueError as e:
        logger.warning(f"Invalid review submission: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error submitting review: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit review",
        ) from e
