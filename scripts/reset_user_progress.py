"""Reset user progress script - Delete all progress data for a specific user."""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import Session, select, delete
from supabase import create_client

from app.config import settings, setup_logging
from app.database import engine
from app.models import CardProgress, ReviewLog, Profile

setup_logging()
logger = logging.getLogger(__name__)


def reset_user_progress(email: str) -> None:
    """
    Reset all progress for a user by email.

    Deletes:
    - All CardProgress entries
    - All ReviewLog entries
    - Resets Profile.current_level to 1

    Args:
        email: User's email address
    """
    logger.info(f"Starting progress reset for user: {email}")

    # Initialize Supabase client
    supabase = create_client(settings.supabase_url, settings.supabase_service_key)

    # Get user ID from Supabase Auth
    try:
        # Use admin API to get user by email
        response = supabase.auth.admin.list_users()
        user = None
        for u in response:
            if u.email == email:
                user = u
                break

        if not user:
            logger.error(f"User not found with email: {email}")
            return

        user_id = user.id
        logger.info(f"Found user ID: {user_id}")

    except Exception as e:
        logger.error(f"Error fetching user from Supabase: {e}", exc_info=True)
        return

    # Delete progress data
    with Session(engine) as session:
        # Count current data
        card_progress_count = session.exec(
            select(CardProgress).where(CardProgress.user_id == user_id)
        ).all()
        review_log_count = session.exec(
            select(ReviewLog).where(ReviewLog.user_id == user_id)
        ).all()

        logger.info(f"Found {len(card_progress_count)} CardProgress entries")
        logger.info(f"Found {len(review_log_count)} ReviewLog entries")

        # Delete CardProgress
        session.exec(delete(CardProgress).where(CardProgress.user_id == user_id))
        logger.info("Deleted all CardProgress entries")

        # Delete ReviewLog
        session.exec(delete(ReviewLog).where(ReviewLog.user_id == user_id))
        logger.info("Deleted all ReviewLog entries")

        # Reset Profile
        profile = session.get(Profile, user_id)
        if profile:
            profile.current_level = 1
            session.add(profile)
            logger.info("Reset current_level to 1")
        else:
            logger.warning("Profile not found - may need to be created")

        session.commit()
        logger.info(f"Successfully reset all progress for user {email}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python reset_user_progress.py <email>")
        sys.exit(1)

    email = sys.argv[1]

    # Confirm before proceeding
    print(f"\n⚠️  WARNING: This will delete ALL progress data for user: {email}")
    print("This includes:")
    print("  - All card progress (CardProgress)")
    print("  - All review history (ReviewLog)")
    print("  - Reset current level to 1")
    print("\nThis action CANNOT be undone!\n")

    confirmation = input("Type 'DELETE' to confirm: ")

    if confirmation != "DELETE":
        print("Aborted.")
        sys.exit(0)

    try:
        reset_user_progress(email)
    except Exception as e:
        logger.error(f"Error resetting user progress: {e}", exc_info=True)
        sys.exit(1)
