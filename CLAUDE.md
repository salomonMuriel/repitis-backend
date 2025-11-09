# Repitis - Spanish Reading App for Kids

A spaced-repetition learning app designed to teach children (ages 4-7) to read in Spanish using the FSRS algorithm and progressive difficulty levels.

We are currently building an MVP. We should keep it as feature-light as possible (while having the frontend still look nice).

## Project Overview

**Goal:** Help children learn to read Spanish through 10 progressive levels (vowels → syllables → words → complex patterns).

**Key Features:**
- FSRS-based spaced repetition for optimal learning
- Audio pronunciation for each card (plays immediately on card flip)
- Visual illustrations for vocabulary
- "Nueva" badge on first-time cards for visual feedback
- Progress tracking with streaks and statistics (new cards + total reviews)
- 10 difficulty levels with ~380 total cards

## Tech Stack

**Frontend:**
- React 19 + TypeScript + Vite
- TanStack Query (data fetching)
- Zustand (state management)
- Framer Motion (animations)
- Tailwind CSS
- Supabase Auth

**Backend:**
- FastAPI (Python 3.11+)
- SQLModel (ORM)
- Alembic (migrations)
- py-fsrs (spaced repetition)
- Eleven Labs (TTS audio generation)
- Supabase Auth integration
- uv (package manager)

**Database:**
- Supabase PostgreSQL
- Row Level Security (RLS)
- JSONB for FSRS state storage
- Alembic for version-controlled migrations

## Architecture

```
Frontend (React) ←→ Backend API (FastAPI) ←→ Database (Supabase PostgreSQL)
                         ↓
                   FSRS Service (py-fsrs)
```

**API Endpoints (MVP):**
- `GET /api/v1/cards/next` - Get next card (backend selects due or new, includes `is_new` flag)
- `POST /api/v1/cards/{id}/review` - Submit review (rating 1-4)
- `GET /api/v1/stats` - User statistics (calculated on-demand)
- `GET /api/v1/stats/today` - Today's session stats (new cards + total reviews)
- `GET /api/v1/levels` - List levels with progress

**Database Schema:**
- `profiles` - User data
- `levels` - 10 difficulty levels
- `cards` - ~380 learning cards
- `card_progress` - FSRS state per user/card
- `review_logs` - Review history (immutable)

## Technical Documentation

- **[FRONTEND.md](./FRONTEND.md)** - React architecture, component guidelines, performance strategies
- **[BACKEND.md](./BACKEND.md)** - FastAPI architecture, FSRS integration, API design
- **[DATABASE.md](./DATABASE.md)** - Schema design, RLS policies, query optimization

## Development Setup

### Backend
```bash
cd backend
cp .env.example .env
# Configure Supabase and Eleven Labs credentials in .env
uv run alembic upgrade head             # Run migrations
uv run python scripts/seed_levels.py    # Seed static data
uv run python scripts/seed_cards.py     # Seed cards
uv run uvicorn app.main:app --reload
# API docs: http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env
# Configure Supabase credentials in .env
npm run dev
# App: http://localhost:5173
```

## Common Commands

**Run tests:**
```bash
cd backend && pytest
cd frontend && npm test
```

**Database migrations:**
```bash
cd backend
alembic revision --autogenerate -m "description"  # Create migration
alembic upgrade head                               # Apply migrations
alembic downgrade -1                               # Rollback last migration
```

**Database seed:**
```bash
cd backend
uv run python scripts/seed_levels.py
uv run python scripts/seed_cards.py
```

**Audio generation (Eleven Labs TTS → Supabase Storage → Database):**
```bash
cd backend
uv run python scripts/generate_and_update_audio.py            # All 363 cards
uv run python scripts/generate_and_update_audio.py --card-id vowel_a_lower  # Single card
# Generates MP3 audio, uploads to Supabase, updates card.audio_url
```

**Reset user progress:**
```bash
cd backend
uv run python scripts/reset_user_progress.py user@example.com
```

**Build frontend:**
```bash
cd frontend && npm run build
```

## Important Guidelines

- Always go for the simplest solution. 
- Don't add any unnecessary complexity.

## Code Guidelines

- **Python:** Type hints, async/await for I/O, snake_case naming, SQLModel for tables
- **TypeScript:** Strict mode, functional components, custom hooks for logic reuse
- **API:** RESTful design, consistent error responses, JWT auth via Supabase
- **Database:** SQLModel as source of truth, Alembic for migrations, RLS for security, JSONB for FSRS state

## Project Structure Notes

- Audio: MP3 files generated with Eleven Labs TTS, stored in Supabase Storage (`audio-files` bucket)
- Images (future): Will be stored in `frontend/public/` or Supabase Storage
- FSRS state: Serialized as JSONB in `card_progress` table (py-fsrs has built-in to_dict/from_dict)
- FSRS analytics: ReviewLog data stored in `review_logs.fsrs_data` (JSONB) for future analytics
- User stats: Calculated on-demand from `review_logs` (no denormalization for MVP)
- Review logs: Immutable (insert-only)
- Database schema: SQLModel tables are source of truth, Alembic generates migrations
- Package management: Use `uv add <package>` to add new dependencies
- Timezone-aware datetimes: All timestamps use UTC timezone (datetime.now(timezone.utc))

## Important Patterns

**FSRS Flow:**
1. User reviews card with rating (1=Again, 2=Hard, 3=Good, 4=Easy)
2. Backend updates FSRS state using py-fsrs, calculates next review time
3. Insert review log (immutable)
4. Return next card or null (session complete)

**Card Progression:**
- New cards introduced from current level
- Due cards prioritized by next_review timestamp
- Max 10 new cards per day
- Max 20 total reviews per day (allows immediate retry of failed cards)
- Learning steps: 1 minute (immediate retry), 18 hours (next-day flexibility)
- Level unlocks based on mastery threshold

---

For detailed implementation guidance, see FRONTEND.md, BACKEND.md, and DATABASE.md.