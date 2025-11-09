"""Supabase JWT authentication dependency."""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

from app.config import settings

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer()

# Supabase client (singleton)
_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client singleton.

    Returns:
        Client: Supabase client instance
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_service_key,
        )
        logger.info("Supabase client initialized")
    return _supabase_client


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> str:
    """
    Validate Supabase JWT token and extract user ID.

    This dependency validates the JWT token with Supabase and returns the authenticated user ID.
    Raises HTTP 401 if the token is invalid or expired.

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        str: Authenticated user ID from Supabase

    Raises:
        HTTPException: 401 if token is invalid or expired

    Example:
        ```python
        @router.get("/profile")
        async def get_profile(user_id: CurrentUser):
            return {"user_id": user_id}
        ```
    """
    token = credentials.credentials
    supabase = get_supabase_client()

    try:
        # Validate JWT token with Supabase
        response = supabase.auth.get_user(token)

        if not response or not response.user:
            logger.warning("Invalid or expired JWT token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = response.user.id
        logger.debug(f"User authenticated: {user_id}")
        return user_id

    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# Type alias for user dependency
CurrentUser = Annotated[str, Depends(get_current_user)]
