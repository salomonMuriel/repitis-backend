"""API route handlers."""

from app.routes.cards import router as cards_router
from app.routes.levels import router as levels_router
from app.routes.stats import router as stats_router

__all__ = [
    "cards_router",
    "levels_router",
    "stats_router",
]
