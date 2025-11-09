# Database Technical Documentation

## Database Provider

**Supabase PostgreSQL**
- Hosted PostgreSQL database
- Built-in Row Level Security (RLS)
- Real-time subscriptions available
- Automatic backups
- RESTful API auto-generated

---

## Schema Overview (MVP)

The database consists of **5 tables** (minimal viable schema):

1. **profiles** - User profile information (extends Supabase auth.users)
2. **levels** - Reading difficulty levels (1-10)
3. **cards** - Learning cards (letters, syllables, words)
4. **card_progress** - User's FSRS state per card
5. **review_logs** - Immutable history of all card reviews

---

## Architecture Guidelines

### Database Design Principles

1. **Simplicity First:** MVP schema with minimal tables (5 total)
2. **JSONB for Flexibility:** Store FSRS state and analytics as JSONB (py-fsrs has built-in serialization)
3. **Strategic Indexes:** Only indexes for critical query paths
4. **RLS for Security:** Enforce data isolation at database level
5. **Stats on-demand:** Calculate analytics from review_logs (no denormalization)
6. **SQLModel as Source of Truth:** Define schema in Python, use Alembic to generate migrations
7. **Version-Controlled Migrations:** All schema changes tracked via Alembic
8. **Timezone-Aware Timestamps:** All datetime fields use UTC timezone (datetime.now(timezone.utc))

### Relationships

```
auth.users (Supabase) 1:1 profiles
profiles 1:many card_progress
profiles 1:many review_logs
levels 1:many cards
cards 1:many card_progress
cards 1:many review_logs
```

### Data Flow

```
User submits review
  ↓
Backend validates request
  ↓
Update card_progress (FSRS state)
  ↓
Insert review_logs (immutable record)
```

---

## Schema Definition Workflow

**SQLModel → Alembic → PostgreSQL**

1. Define/modify SQLModel tables in `app/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review generated migration in `alembic/versions/`
4. Apply to Supabase: `alembic upgrade head`
5. Add RLS policies manually in Supabase (Alembic doesn't handle RLS)

**Benefits:**
- Single source of truth (Python code)
- Auto-generated migrations
- Version-controlled schema evolution
- Type safety in application code

---

## Table Descriptions

All tables defined as SQLModel classes, migrated via Alembic.

### profiles

Extends Supabase's `auth.users` with application-specific data.

**Purpose:** Store user name and current level progression

**Key Fields:**
- `id` (UUID): Primary key, references Supabase auth.users
- `name` (TEXT): Display name
- `current_level` (INTEGER): Current difficulty level (default 1)
- `created_at` (TIMESTAMP): Account creation time
- `updated_at` (TIMESTAMP): Last profile update

**Design Notes:**
- One-to-one with auth.users
- RLS ensures users only see their own profile
- `current_level` allows filtering cards by level ≤ current_level
- User preferences/settings hardcoded in frontend for MVP

---

### levels

Defines the 10 reading difficulty levels.

**Purpose:** Organize cards by difficulty progression

**Key Fields:**
- `id` (SERIAL): Auto-incrementing primary key
- `name` (TEXT): Level name (e.g., "Vowels")
- `order_index` (INTEGER): Display order (unique)

**Design Notes:**
- Static data seeded at initialization
- Public read access (no RLS restrictions)
- Levels are sequential and immutable
- Mastery threshold (e.g., 80%) hardcoded in backend logic

**Level Progression:**
1. Vowels
2. Easy Syllables (m, n, p, s, l)
3. All Simple Syllables
4. Two-Syllable Words
5. Closed Syllables
6. Proper Nouns & Capitalization
7. Digraphs (ch, ll, rr)
8. Consonant Clusters (br, tr, pl, etc.)
9. Multi-Syllable Words
10. Diphthongs & Advanced

---

### cards

Individual learning items (~380 total across all levels).

**Purpose:** Store card content and media references

**Key Fields:**
- `id` (UUID): Primary key
- `level_id` (INTEGER): Foreign key to levels
- `content` (TEXT): The letter, syllable, or word
- `content_type` (TEXT): Type classification ('vowel', 'syllable', 'word', 'proper_noun')
- `image_url` (TEXT): Visual illustration path (Supabase Storage or AI-generated)
- `audio_url` (TEXT): Pronunciation audio path (Supabase Storage or AI-generated)

**Design Notes:**
- Immutable once seeded
- Public read access
- Media files stored in Supabase Storage or generated on-the-fly with AI
- Card order determined by FSRS algorithm (no order_index needed)
- Keep schema minimal for MVP (metadata/categories can be added later)

---

### card_progress

User-specific FSRS algorithm state for each card.

**Purpose:** Track learning progress and schedule reviews

**Key Fields:**
- `user_id` (UUID): Foreign key to profiles
- `card_id` (UUID): Foreign key to cards
- `fsrs_state` (JSONB): Serialized FSRS Card state (includes card_id for tracking)
- `next_review` (TIMESTAMP): When card is due (timezone-aware UTC)
- `last_review` (TIMESTAMP): Last review timestamp (timezone-aware UTC)
- `created_at` (TIMESTAMP): First learning timestamp (timezone-aware UTC)

**Design Notes:**
- Unique constraint on (user_id, card_id)
- JSONB stores FSRS state flexibly
- Indexed on (user_id, next_review) for efficient queries
- RLS ensures users only see their own progress
- All timestamps use timezone-aware UTC for consistency

**FSRS State Structure:**
```json
{
  "due": "2024-01-15T10:30:00Z",
  "stability": 2.5,
  "difficulty": 0.3,
  "elapsed_days": 1,
  "scheduled_days": 3,
  "reps": 5,
  "lapses": 0,
  "state": 2,
  "last_review": "2024-01-12T10:30:00Z"
}
```

---

### review_logs

Immutable audit log of all card reviews.

**Purpose:** Analytics and progress tracking

**Key Fields:**
- `id` (UUID): Primary key
- `user_id` (UUID): Foreign key to profiles
- `card_id` (UUID): Foreign key to cards
- `rating` (INTEGER): 1=Again, 2=Hard, 3=Good, 4=Easy
- `reviewed_at` (TIMESTAMP): Review timestamp (timezone-aware UTC)
- `fsrs_data` (JSONB): FSRS ReviewLog data for analytics

**Design Notes:**
- Insert-only (no updates/deletes)
- Indexed on (user_id, reviewed_at) for analytics
- Used to calculate stats on-demand (reviews today, total reviews, etc.)
- RLS ensures users only see their own logs
- FSRS analytics stored in flexible JSONB format for future dashboard features

**FSRS Data Structure:**
```json
{
  "card_id": "vowel_a_lower",
  "rating": 3,
  "review_datetime": "2025-10-14T14:36:55+00:00",
  "review_duration": null
}
```

---

## Indexing Strategy

### Minimal Index Set for MVP

```sql
-- 1. Due cards query (most frequent)
CREATE INDEX idx_card_progress_next_review
ON card_progress(user_id, next_review);

-- 2. Review history analytics
CREATE INDEX idx_review_logs_user_reviewed
ON review_logs(user_id, reviewed_at DESC);

-- 3. Card-level joins
CREATE INDEX idx_cards_level
ON cards(level_id);
```

**Note:** Primary key on `card_progress(user_id, card_id)` is automatically indexed, no additional index needed for user lookups.

---

## Row Level Security (RLS)

### Security Model

**Principle:** Users can only access their own data

**Implementation:**
- RLS enabled on all user-specific tables
- Policies use `auth.uid()` to match user_id
- Cards and levels are public (read-only)
- Service role key bypasses RLS (backend only)

### Policy Guidelines

1. **SELECT policies:** Allow users to view own data
2. **INSERT policies:** Allow users to create own data
3. **UPDATE policies:** Allow users to modify own data
4. **DELETE policies:** Typically restricted (soft deletes preferred)

---

## Query Optimization

### Common Query Patterns

All card selection logic is handled internally by the backend. The main queries are:

1. **Today's review count (for daily limit check):**
   ```sql
   SELECT COUNT(*) FROM review_logs
   WHERE user_id = $1 AND reviewed_at >= CURRENT_DATE;
   ```
   Used to enforce max 20 reviews per day (allows immediate retry + next-day cards)

2. **Level progress:**
   ```sql
   SELECT COUNT(*) FROM card_progress
   WHERE user_id = $1 AND card_id IN (
     SELECT id FROM cards WHERE level_id = $2
   );
   ```

3. **User profile lookup:**
   ```sql
   SELECT * FROM profiles WHERE id = $1;
   ```

**Note:** Card selection (due cards, new cards, FSRS scheduling) is handled by backend service layer, not exposed as direct queries.

---

## Data Integrity

### Constraints

- **Primary Keys:** All tables have primary keys
- **Foreign Keys:** Enforce referential integrity
- **Unique Constraints:** (user_id, card_id) in card_progress
- **NOT NULL:** Critical fields like user_id, card_id
- **ON DELETE CASCADE:** Automatic cleanup of dependent records

### Validation

- **Application Layer:** Validate rating values (1-4)
- **Database Layer:** Enforce data types and constraints
- **JSONB Schema:** Validate FSRS state structure in application

---

## Backup & Recovery

### Backup Strategy

1. **Automatic Backups:** Supabase daily backups (paid plans)
2. **Manual Exports:** Use pg_dump for critical tables
3. **Priority Tables:** profiles, card_progress, review_logs

### Recovery Procedures

- Test restore process regularly
- Keep backups for 30 days minimum
- Document recovery steps
- Export data before major migrations

---

## Scalability Considerations

### Current Scale (MVP)
- ~380 cards (static)
- Hundreds of users (initial launch)
- Thousands of reviews per day

### Future Growth Planning

1. **review_logs growth:** Consider partitioning by date if > millions of rows
2. **Caching:** Add Redis if profile/stats queries become bottleneck
3. **Monitoring:** Use Supabase dashboard to track query performance

**For MVP:** Current schema handles expected scale without optimization.

---

## Migration Strategy

### Initial Setup with Alembic

1. **Initialize Alembic:**
   ```bash
   alembic init alembic
   ```

2. **Configure Alembic** (`alembic.ini`):
   - Set `sqlalchemy.url` to Supabase PostgreSQL connection string
   - Import SQLModel metadata in `alembic/env.py`

3. **Create initial migration:**
   ```bash
   alembic revision --autogenerate -m "initial schema"
   ```

4. **Apply migration to Supabase:**
   ```bash
   alembic upgrade head
   ```

5. **Add RLS policies manually** in Supabase SQL editor (Alembic doesn't handle RLS)

6. **Seed data:**
   ```bash
   python scripts/seed_levels.py
   python scripts/seed_cards.py
   ```

### Future Migrations

1. Modify SQLModel classes in `app/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review generated SQL in `alembic/versions/`
4. Test on local/staging database first
5. Apply to production: `alembic upgrade head`
6. Update RLS policies if needed (manually)

**Best Practices:**
- Always review auto-generated migrations before applying
- Test migrations with rollback: `alembic downgrade -1`
- Version control all migration files
- Never edit applied migrations - create new ones

---

## Setup Instructions

1. **Create Supabase project** at https://supabase.com
2. **Copy connection details:**
   - Project URL
   - Anon key (for frontend)
   - Service role key (for backend)
   - PostgreSQL connection string (for Alembic)

3. **Configure backend environment** (`.env`):
   ```env
   DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres
   SUPABASE_URL=https://[project].supabase.co
   SUPABASE_SERVICE_KEY=your_service_key
   ```

4. **Initialize Alembic:**
   ```bash
   cd backend
   alembic init alembic
   # Configure alembic.ini and env.py
   ```

5. **Create and apply initial migration:**
   ```bash
   alembic revision --autogenerate -m "initial schema"
   alembic upgrade head
   ```

6. **Add RLS policies** in Supabase SQL editor

7. **Seed data:**
   ```bash
   python scripts/seed_levels.py
   python scripts/seed_cards.py
   ```

---

## Monitoring & Maintenance

### Key Metrics (MVP)

- Query response times (via Supabase dashboard)
- Table sizes (monitor review_logs growth)
- Failed queries / errors

### Maintenance

Supabase handles routine maintenance (vacuuming, backups) automatically.

Monitor Supabase dashboard for slow queries and optimize as needed.
