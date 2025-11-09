"""
Backfill highest_stability and mastered_at for existing card_progress entries.

This script uses the current FSRS stability as a best-effort estimate for highest_stability.
For mastered_at, we use created_at if current stability >= 7 days.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine


def backfill_mastery_data():
    """Backfill highest_stability and mastered_at fields."""

    with engine.connect() as conn:
        # First, check how many rows need updating
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM card_progress
            WHERE highest_stability = 0.0
        """))
        rows_to_update = result.scalar()

        print(f"Found {rows_to_update} card_progress entries to backfill")

        if rows_to_update == 0:
            print("No rows to update. Exiting.")
            return

        # Backfill the data
        result = conn.execute(text("""
            UPDATE card_progress
            SET
                highest_stability = (fsrs_state->>'stability')::float,
                mastered_at = CASE
                    WHEN (fsrs_state->>'stability')::float >= 7.0 THEN created_at
                    ELSE NULL
                END
            WHERE highest_stability = 0.0
        """))

        conn.commit()

        print(f"✅ Updated {result.rowcount} rows")

        # Show summary statistics
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total_cards,
                COUNT(CASE WHEN highest_stability >= 7.0 THEN 1 END) as mastered_cards,
                AVG(highest_stability) as avg_stability,
                MAX(highest_stability) as max_stability
            FROM card_progress
        """))

        row = result.fetchone()
        print("\nSummary:")
        print(f"  Total cards: {row[0]}")
        print(f"  Mastered cards (≥7 days): {row[1]}")
        print(f"  Average stability: {row[2]:.2f} days")
        print(f"  Max stability: {row[3]:.2f} days")


if __name__ == "__main__":
    print("Backfilling mastery data for existing card_progress entries...\n")
    backfill_mastery_data()
    print("\n✅ Backfill complete!")
