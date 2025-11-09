"""Check which cards have incorrect audio URLs."""
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlmodel import Session, create_engine, select
from app.models.card import Card
from app.config import settings

def check_card_urls():
    """Check which cards have incorrect audio URLs."""
    engine = create_engine(str(settings.database_url))

    with Session(engine) as session:
        # Get all cards
        statement = select(Card).order_by(Card.level_id, Card.id)
        cards = session.exec(statement).all()

        correct_count = 0
        incorrect_count = 0
        null_count = 0

        print(f"\n{'='*80}")
        print(f"CARD AUDIO URL CHECK REPORT")
        print(f"{'='*80}\n")

        incorrect_cards = []
        null_cards = []

        for card in cards:
            if card.audio_url is None:
                null_count += 1
                null_cards.append(card)
            elif card.audio_url.startswith('https://'):
                correct_count += 1
            else:
                incorrect_count += 1
                incorrect_cards.append(card)

        # Summary
        print(f"SUMMARY:")
        print(f"  Total cards: {len(cards)}")
        print(f"  ✅ Correct URLs (https://): {correct_count}")
        print(f"  ❌ Incorrect URLs: {incorrect_count}")
        print(f"  ⚠️  NULL URLs: {null_count}")
        print()

        # Show incorrect URLs
        if incorrect_cards:
            print(f"\n{'='*80}")
            print(f"CARDS WITH INCORRECT URLs ({len(incorrect_cards)} cards):")
            print(f"{'='*80}\n")
            for card in incorrect_cards:
                print(f"ID: {card.id}")
                print(f"  Level: {card.level_id}")
                print(f"  Content: {card.content}")
                print(f"  Current URL: {card.audio_url}")
                print()

        # Show NULL URLs
        if null_cards:
            print(f"\n{'='*80}")
            print(f"CARDS WITH NULL URLs ({len(null_cards)} cards):")
            print(f"{'='*80}\n")
            for card in null_cards:
                print(f"ID: {card.id}")
                print(f"  Level: {card.level_id}")
                print(f"  Content: {card.content}")
                print()

if __name__ == "__main__":
    check_card_urls()
