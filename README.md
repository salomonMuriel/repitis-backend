# Backend Technical Documentation

## Tech Stack

- **Framework:** FastAPI
- **Language:** Python 3.11+
- **Database ORM:** SQLModel
- **Migrations:** Alembic
- **Database:** Supabase PostgreSQL
- **Auth:** Supabase Auth
- **Spaced Repetition:** py-fsrs
- **Audio TTS:** Eleven Labs
- **Package Manager:** uv

---

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app + CORS setup
│   ├── config.py                  # Settings (Pydantic BaseSettings)
│   ├── database.py                # Engine + session dependency
│   ├── auth.py                    # JWT validation dependency
│   │
│   ├── models/                    # SQLModel table definitions (source of truth)
│   │   ├── __init__.py
│   │   ├── profile.py
│   │   ├── level.py
│   │   ├── card.py
│   │   ├── card_progress.py
│   │   └── review_log.py
│   │
│   ├── schemas/                   # Response models ONLY (API contracts)
│   │   ├── __init__.py
│   │   ├── card.py               # CardResponse, NextCardResponse
│   │   ├── review.py             # ReviewRequest, ReviewResponse
│   │   └── stats.py              # StatsResponse, TodayStatsResponse
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── fsrs.py               # FSRS wrapper (thin service layer)
│   │   └── cards.py              # Card selection business logic
│   │
│   └── routes/
│       ├── __init__.py
│       ├── cards.py              # GET /next, POST /{id}/review
│       ├── stats.py              # GET /stats
│       └── levels.py             # GET /levels
│
├── alembic/                       # Database migrations
│   ├── versions/                  # Migration files
│   └── env.py                     # Alembic config
│
├── scripts/
│   ├── seed_levels.py
│   ├── seed_cards.py
│   ├── generate_and_update_audio.py
│   ├── reset_user_progress.py    # Delete all progress for user
│   └── upload_audio.py
│
├── tests/
│   ├── test_fsrs.py
│   ├── test_cards.py
│   └── test_auth.py
│
├── alembic.ini                    # Alembic configuration
├── requirements.txt
├── pyproject.toml
└── .env.example
```

---

## Architecture Overview

### Layered Architecture

1. **Routes Layer** (`routes/`)
   - API endpoint definitions
   - Request/response handling
   - Dependency injection (auth via `CurrentUser`, database via `SessionDep`)
   - Minimal logic - delegates to services

2. **Services Layer** (`services/`)
   - Business logic implementation
   - FSRS algorithm wrapper (thin layer over py-fsrs)
   - Card selection logic with explicit rules
   - Statistics calculated on-demand from review_logs

3. **Models Layer** (`models/`)
   - SQLModel table definitions (combines ORM + Pydantic)
   - Database schema as Python classes
   - NOT exposed directly via API (security)

4. **Schemas Layer** (`schemas/`)
   - Response models ONLY (API contracts)
   - Separate from database models for security
   - Controls exactly what data is exposed to clients
   - Type-safe request/response validation

---

## Code Guidelines

### General Principles

- **Type Hints:** Use Python type hints for all function signatures
- **Async/Await:** Use async endpoints for I/O operations
- **Dependency Injection:** Use `Annotated` types for cleaner dependencies (`SessionDep`, `CurrentUser`)
- **Error Handling:** Return appropriate HTTP status codes and error messages
- **Documentation:** Use docstrings for all public functions and classes
- **Separation of Concerns:** Database models (SQLModel) ≠ API responses (Pydantic schemas)

### Naming Conventions

- **Files:** snake_case (e.g., `card_service.py`)
- **Classes:** PascalCase (e.g., `CardService`)
- **Functions/Variables:** snake_case (e.g., `get_due_cards`)
- **Constants:** UPPER_SNAKE_CASE (e.g., `MAX_CARDS_PER_SESSION`)

### API Design

- **RESTful Endpoints:** Follow REST conventions
- **Versioning:** Prefix routes with `/api/v1/` for future compatibility
- **Response Format:** Consistent JSON structure for success and errors
- **Minimal Endpoints:** Keep MVP focused (4 core routes)
- **No Pagination for MVP:** ~380 cards total, pagination unnecessary initially

---

## Core Components

### Database Session Dependency

Modern SQLModel pattern using `Annotated` types:

```python
# database.py
from sqlmodel import Session, create_engine
from typing import Annotated
from fastapi import Depends

engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]
```

Usage in routes:
```python
@router.get("/cards/next")
async def get_next_card(session: SessionDep, user_id: CurrentUser):
    ...
```

### Auth Dependency

JWT validation using Supabase:

```python
# auth.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from typing import Annotated

security = HTTPBearer()

async def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> str:
    """Validate Supabase JWT and return user_id"""
    token = credentials.credentials
    # Validate with supabase.auth.get_user(token)
    # Return user_id or raise HTTPException(401)
    ...

CurrentUser = Annotated[str, Depends(get_current_user)]
```

### FSRS Service

Thin wrapper around py-fsrs library:

```python
# services/fsrs.py
from fsrs import FSRS, Card, Rating

class FSRSService:
    def __init__(self):
        self.scheduler = FSRS(
            desired_retention=0.9,
            learning_steps=(1, 10),
            maximum_interval=365
        )

    def create_new_card(self) -> dict:
        """Create initial FSRS state for new card"""
        card = Card()
        return card.to_dict()  # Built-in serialization

    def review_card(self, fsrs_state: dict, rating: int) -> tuple[dict, datetime]:
        """Process review and return updated state + next_review"""
        card = Card.from_dict(fsrs_state)
        rating_enum = Rating(rating)  # 1=Again, 2=Hard, 3=Good, 4=Easy
        scheduling_cards = self.scheduler.repeat(card, datetime.now())
        updated_card = scheduling_cards[rating_enum]
        return updated_card.to_dict(), updated_card.due
```

**Key Parameters (Optimized for Children):**
- `desired_retention`: 0.9 (90% retention target)
- `learning_steps`: (1, 1080) minutes (1 min immediate retry, 18 hours for next-day flexibility)
- `maximum_interval`: 365 days
- `max_new_cards_per_day`: 10
- `max_reviews_per_day`: 20 (total reviews including retries)

### Card Service

Handles card selection with explicit business rules:

```python
# services/cards.py
class CardService:
    MAX_NEW_CARDS_PER_DAY = 10  # Business rule

    @staticmethod
    def get_next_card(session: Session, user_id: str) -> tuple[Card | None, bool]:
        """
        Selection algorithm:
        1. Check for due cards (next_review <= now)
        2. If none, get new card from current level or below
        3. Enforce daily new card limit

        Returns: (card, is_new) - Tuple indicating if card is new
        """
        # Implementation...
```

**Card Selection Rules:**
- Check daily review limit (20 total reviews per day)
- Prioritize due cards by `next_review` timestamp
- If no due cards, select new cards from `current_level` or below
- Max 10 new cards per day
- Returns `(card, is_new)` tuple - `is_new=True` when card has no prior progress
- Return `(None, False)` when session complete

### Stats Calculation

User statistics calculated on-demand from review_logs and card_progress:
- **Full Stats** (`GET /stats`): Today's reviews, total reviews, streaks, level progress
- **Today Stats** (`GET /stats/today`): Lightweight endpoint for review sessions
  - `new_cards_today`: Count of cards with `CardProgress.created_at >= today_start`
  - `total_reviews_today`: Count of `ReviewLog` entries today

---

## Database Models

### SQLModel Tables (MVP)

SQLModel combines ORM with Pydantic validation. These models are NOT exposed directly via API.

Example structure:

```python
# models/card_progress.py
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from datetime import datetime
from typing import Optional

class CardProgress(SQLModel, table=True):
    user_id: str = Field(foreign_key="profile.id", primary_key=True)
    card_id: str = Field(foreign_key="card.id", primary_key=True)
    fsrs_state: dict = Field(sa_column=Column(JSON))  # JSONB
    next_review: datetime
    last_review: Optional[datetime] = None
```

**Key Tables:**
1. **Profile** - User name and current level
2. **Level** - Reading difficulty levels (1-10)
3. **Card** - Individual learning items (letters, syllables, words)
4. **CardProgress** - User-specific FSRS state per card (JSONB)
5. **ReviewLog** - Immutable review history with FSRS analytics (JSONB)

### Response Schemas (Security Boundary)

Separate Pydantic models control API responses:

```python
# schemas/card.py
from pydantic import BaseModel

class CardResponse(BaseModel):
    id: str
    content: str
    content_type: str
    image_url: str | None
    audio_url: str | None
    level_id: int
    is_new: bool  # True if card has no prior progress
    # Excludes internal fields like created_at, etc.
```

### Data Flow

```
User requests next card → GET /api/v1/cards/next
  ↓
CardService.get_next_card(session, user_id)
  ↓
Backend decides: due card or new card
  ↓
Return NextCardResponse (schema) to frontend

User reviews card → POST /api/v1/cards/{id}/review
  ↓
CardService.submit_review(session, user_id, card_id, rating)
  ↓
FSRSService.review_card(fsrs_state, rating)
  ↓
Update CardProgress (FSRS state)
  ↓
Insert ReviewLog entry
  ↓
Return ReviewResponse (schema) to frontend
```

---

## API Endpoints (MVP)

**5 core endpoints:**

### Cards
```python
GET  /api/v1/cards/next
```
- Returns next card (due or new) based on backend selection algorithm
- Includes `is_new` flag to indicate first-time cards
- Returns `null` when session complete (no due cards + daily new card limit reached)
- Response: `NextCardResponse | null`

```python
POST /api/v1/cards/{card_id}/review
```
- Submit review with rating (1=Again, 2=Hard, 3=Good, 4=Easy)
- Request body: `{ "rating": int }`
- Response: `ReviewResponse`

### Stats
```python
GET  /api/v1/stats
```
- Get all user statistics in one response (calculated on-demand)
- Includes: today's count, total reviews, level progress, streak
- Response: `StatsResponse`

```python
GET  /api/v1/stats/today
```
- Lightweight endpoint for real-time review session tracking
- Returns: `{ "new_cards_today": int, "total_reviews_today": int }`
- Response: `TodayStatsResponse`

### Levels
```python
GET  /api/v1/levels
```
- List all 10 levels with user's progress percentages
- Response: `list[LevelResponse]`

### Auth
- All endpoints protected by JWT validation (Supabase Auth)
- Token passed via `Authorization: Bearer <token>` header
- Dependency extracts `user_id` from token

---

## Testing Strategy

### Unit Tests
- Test individual services in isolation
- Mock database sessions
- Test FSRS calculations
- Validate business logic

### Integration Tests
- Test API endpoints end-to-end
- Use test database
- Verify request/response contracts
- Test authentication flow

### Test Coverage
- Aim for >80% code coverage
- Focus on critical business logic (FSRS, card scheduling)
- Test edge cases (empty queues, new users, etc.)

---

## Environment Variables

```env
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key
DATABASE_URL=postgresql://...
ELEVEN_LABS_API_KEY=your_eleven_labs_key
ENVIRONMENT=development|production
LOG_LEVEL=INFO|DEBUG
```

---

## Deployment

### Recommended: Railway
- Easy Python deployment
- Auto-deploy from GitHub
- Built-in PostgreSQL (or use Supabase)
- Environment variable management

### Alternatives
- **Render:** Free tier, containerized deployment
- **Fly.io:** Global edge deployment
- **Docker:** Containerize with Dockerfile

### Deployment Checklist
- [ ] Set production environment variables
- [ ] Enable CORS for frontend domain
- [ ] Configure logging
- [ ] Set up monitoring (Sentry, DataDog)
- [ ] Run database migrations
- [ ] Seed initial data (levels, cards)

---

## Setup Instructions

```bash
cd backend
cp .env.example .env
# Edit .env with Supabase and Eleven Labs credentials
uv run alembic upgrade head
uv run python scripts/seed_levels.py
uv run python scripts/seed_cards.py
uv run python scripts/generate_and_update_audio.py  # Optional: Generate all audio
uv run uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive API documentation!

**Audio Generation:**
- Uses Eleven Labs TTS API to generate MP3 audio files
- Uploads to Supabase Storage (`audio-files` bucket)
- Updates `card.audio_url` in database
- Run `uv run python scripts/generate_and_update_audio.py` for all 363 cards (~15 mins)
