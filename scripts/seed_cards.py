"""Seed script for cards table."""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import Session, select

from app.config import settings, setup_logging
from app.database import engine
from app.models import Card

setup_logging()
logger = logging.getLogger(__name__)


# Supabase Storage configuration
BUCKET_NAME = "audio-files"


def get_audio_url(path: str) -> str:
    """
    Generate Supabase Storage URL for audio file.

    Args:
        path: Relative path within bucket (e.g., 'vowels/a.wav')

    Returns:
        Full Supabase Storage URL
    """
    return f"{settings.supabase_url}/storage/v1/object/public/{BUCKET_NAME}/{path}"


# Card generators by level
def generate_level_1_cards() -> list[dict]:
    """Level 1: Vowels (10 cards) - both lowercase and uppercase."""
    cards = []
    vowels = ["a", "e", "i", "o", "u"]

    for vowel in vowels:
        # Lowercase vowel
        cards.append({
            "id": f"vowel_{vowel}_lower",
            "level_id": 1,
            "content": vowel,
            "content_type": "letter",
            "image_url": f"/images/vowels/{vowel}.png",
            "audio_url": get_audio_url(f"vowels/{vowel}.wav"),
        })
        # Uppercase vowel
        cards.append({
            "id": f"vowel_{vowel}_upper",
            "level_id": 1,
            "content": vowel.upper() + vowel,
            "content_type": "letter",
            "image_url": f"/images/vowels/{vowel}_upper.png",
            "audio_url": get_audio_url(f"vowels/{vowel}.wav"),
        })

    return cards


def generate_level_2_cards() -> list[dict]:
    """Level 2: Easy Consonant Syllables (25 cards) - m, n, p, s, l."""
    cards = []
    consonants = ["m", "n", "p", "s", "l"]
    vowels = ["a", "e", "i", "o", "u"]

    for consonant in consonants:
        for vowel in vowels:
            syllable = consonant + vowel
            cards.append({
                "id": f"syllable_{syllable}",
                "level_id": 2,
                "content": syllable,
                "content_type": "syllable",
                "image_url": None,
                "audio_url": get_audio_url(f"syllables/{syllable}.wav"),
            })

    return cards


def generate_level_3_cards() -> list[dict]:
    """Level 3: All Simple Consonant Syllables (60 cards) - remaining consonants."""
    cards = []
    # Consonants: t, d, f, b, c/qu, g/gu, j, v, r, ñ, z
    vowels = ["a", "e", "i", "o", "u"]

    # Simple consonants
    simple_consonants = ["t", "d", "f", "b", "j", "v", "r", "ñ", "z"]
    for consonant in simple_consonants:
        for vowel in vowels:
            syllable = consonant + vowel
            cards.append({
                "id": f"syllable_{syllable}",
                "level_id": 3,
                "content": syllable,
                "content_type": "syllable",
                "image_url": None,
                "audio_url": get_audio_url(f"syllables/{syllable}.wav"),
            })

    # Special c/qu rule
    c_syllables = [
        ("ca", "ca"), ("que", "que"), ("qui", "qui"), ("co", "co"), ("cu", "cu")
    ]
    for syllable_id, syllable in c_syllables:
        cards.append({
            "id": f"syllable_{syllable_id}",
            "level_id": 3,
            "content": syllable,
            "content_type": "syllable",
            "image_url": None,
            "audio_url": get_audio_url(f"syllables/{syllable}.wav"),
        })

    # Special g/gu rule
    g_syllables = [
        ("ga", "ga"), ("gue", "gue"), ("gui", "gui"), ("go", "go"), ("gu", "gu")
    ]
    for syllable_id, syllable in g_syllables:
        cards.append({
            "id": f"syllable_{syllable_id}",
            "level_id": 3,
            "content": syllable,
            "content_type": "syllable",
            "image_url": None,
            "audio_url": get_audio_url(f"syllables/{syllable}.wav"),
        })

    return cards


def generate_level_4_cards() -> list[dict]:
    """Level 4: Two-Syllable Words (40 cards) - simple CV pattern words."""
    words = [
        "casa", "mesa", "pato", "luna", "mono",
        "sapo", "vaca", "boca", "piso", "rana",
        "mano", "pino", "gato", "nido", "ropa",
        "papa", "mama", "taza", "dado", "foto",
        "lana", "pera", "peso", "rata", "sala",
        "tapa", "lobo", "masa", "nota", "pala",
        "ramo", "sopa", "toro", "vaso", "cama",
        "dedo", "foca", "bote", "cono", "lima",
    ]

    cards = []
    for word in words:
        cards.append({
            "id": f"word_{word}",
            "level_id": 4,
            "content": word,
            "content_type": "word",
            "image_url": f"/images/words/{word}.png",
            "audio_url": get_audio_url(f"words/{word}.wav"),
        })

    return cards


def generate_level_5_cards() -> list[dict]:
    """Level 5: Closed Syllables (30 cards) - VC, CVC patterns."""
    words = [
        "sol", "pan", "mar", "dos", "luz",
        "tres", "gol", "sal", "flor", "mes",
        "bus", "cal", "mil", "son", "sur",
        "paz", "red", "voz", "pez", "pin",
        "ten", "fin", "bar", "gas", "col",
        "van", "tan", "por", "con", "ser",
    ]

    cards = []
    for word in words:
        cards.append({
            "id": f"word_{word}",
            "level_id": 5,
            "content": word,
            "content_type": "word",
            "image_url": f"/images/words/{word}.png",
            "audio_url": get_audio_url(f"words/{word}.wav"),
        })

    return cards


def generate_level_6_cards() -> list[dict]:
    """Level 6: Proper Nouns & Capitalization (20 cards) - names and places."""
    proper_nouns = [
        # Names
        "Ana", "Pedro", "Luis", "María", "José",
        "Carmen", "Juan", "Rosa", "Carlos", "Elena",
        # Places
        "México", "España", "Lima", "Cuba", "Chile",
        "Perú", "Panamá", "Miami", "Texas", "Madrid",
    ]

    cards = []
    for noun in proper_nouns:
        cards.append({
            "id": f"proper_{noun.lower()}",
            "level_id": 6,
            "content": noun,
            "content_type": "proper_noun",
            "image_url": f"/images/proper/{noun.lower()}.png",
            "audio_url": get_audio_url(f"proper/{noun.lower()}.wav"),
        })

    return cards


def generate_level_7_cards() -> list[dict]:
    """Level 7: Digraphs (45 cards) - ch, ll, rr."""
    cards = []
    vowels = ["a", "e", "i", "o", "u"]

    # CH syllables
    for vowel in vowels:
        syllable = "ch" + vowel
        cards.append({
            "id": f"syllable_{syllable}",
            "level_id": 7,
            "content": syllable,
            "content_type": "syllable",
            "image_url": None,
            "audio_url": get_audio_url(f"syllables/{syllable}.wav"),
        })

    # LL syllables
    for vowel in vowels:
        syllable = "ll" + vowel
        cards.append({
            "id": f"syllable_{syllable}",
            "level_id": 7,
            "content": syllable,
            "content_type": "syllable",
            "image_url": None,
            "audio_url": get_audio_url(f"syllables/{syllable}.wav"),
        })

    # RR syllables
    for vowel in vowels:
        syllable = "rr" + vowel
        cards.append({
            "id": f"syllable_{syllable}",
            "level_id": 7,
            "content": syllable,
            "content_type": "syllable",
            "image_url": None,
            "audio_url": get_audio_url(f"syllables/{syllable}.wav"),
        })

    # Words with digraphs
    digraph_words = [
        "chocolate", "coche", "leche", "noche", "hacha", "chino",
        "lluvia", "pollo", "gallina", "silla", "calle", "llave",
        "perro", "carro", "torre", "burro", "arroz", "tierra",
    ]

    for word in digraph_words:
        cards.append({
            "id": f"word_{word}",
            "level_id": 7,
            "content": word,
            "content_type": "word",
            "image_url": f"/images/words/{word}.png",
            "audio_url": get_audio_url(f"words/{word}.wav"),
        })

    return cards


def generate_level_8_cards() -> list[dict]:
    """Level 8: Consonant Clusters (60 cards) - pr, br, tr, pl, bl, cl, fl, gr, dr, cr, fr."""
    cards = []
    vowels = ["a", "e", "i", "o", "u"]

    # R-clusters
    r_clusters = ["pr", "br", "tr", "gr", "dr", "cr", "fr"]
    for cluster in r_clusters:
        for vowel in vowels:
            syllable = cluster + vowel
            cards.append({
                "id": f"syllable_{syllable}",
                "level_id": 8,
                "content": syllable,
                "content_type": "syllable",
                "image_url": None,
                "audio_url": get_audio_url(f"syllables/{syllable}.wav"),
            })

    # L-clusters
    l_clusters = ["pl", "bl", "cl", "fl", "gl"]
    for cluster in l_clusters:
        for vowel in vowels:
            syllable = cluster + vowel
            cards.append({
                "id": f"syllable_{syllable}",
                "level_id": 8,
                "content": syllable,
                "content_type": "syllable",
                "image_url": None,
                "audio_url": get_audio_url(f"syllables/{syllable}.wav"),
            })

    return cards


def generate_level_9_cards() -> list[dict]:
    """Level 9: Three+ Syllable Words (50 cards) - complex multi-syllable words."""
    words = [
        "escuela", "elefante", "ventana", "jirafa", "teléfono",
        "océano", "helado", "escalar", "hospital", "profesor",
        "computadora", "dinosaurio", "mariposa", "bicicleta", "árbol",
        "príncipe", "plátano", "pájaro", "médico", "número",
        "televisión", "zapato", "camisa", "pelota", "familia",
        "domingo", "semana", "mañana", "tarde", "temprano",
        "animal", "caballo", "tortuga", "cocodrilo", "calabaza",
        "tomate", "naranja", "manzana", "banana", "sandía",
        "ventilador", "refrigerador", "carpintero", "bombero", "policía",
        "farmacia", "panadería", "biblioteca", "universidad", "restaurante",
    ]

    cards = []
    for word in words:
        cards.append({
            "id": f"word_{word}",
            "level_id": 9,
            "content": word,
            "content_type": "word",
            "image_url": f"/images/words/{word}.png",
            "audio_url": get_audio_url(f"words/{word}.wav"),
        })

    return cards


def generate_level_10_cards() -> list[dict]:
    """Level 10: Diphthongs & Advanced Patterns (40 cards) - complex vowel combinations."""
    words = [
        # Diphthongs
        "baile", "aire", "hay", "vaina",
        "seis", "peine", "rey", "ley",
        "hoy", "oigo", "soy", "convoy",
        "muy", "fui", "ruido", "cuidado",
        "auto", "causa", "jaula", "pausa",
        "Europa", "deuda", "feudal", "eucalipto",
        "ciudad", "triunfo", "viuda", "diurno",
        # Hiatus
        "país", "raíz", "maíz", "baúl",
        # Accent marks
        "ratón", "canción", "último", "música",
        "mamá", "papá", "José", "Andrés",
    ]

    cards = []
    for word in words:
        cards.append({
            "id": f"word_{word}",
            "level_id": 10,
            "content": word,
            "content_type": "word",
            "image_url": f"/images/words/{word}.png",
            "audio_url": get_audio_url(f"words/{word}.wav"),
        })

    return cards


def generate_all_cards() -> list[dict]:
    """Generate all cards for all 10 levels."""
    all_cards = []

    all_cards.extend(generate_level_1_cards())   # 10 cards
    all_cards.extend(generate_level_2_cards())   # 25 cards
    all_cards.extend(generate_level_3_cards())   # ~60 cards
    all_cards.extend(generate_level_4_cards())   # 40 cards
    all_cards.extend(generate_level_5_cards())   # 30 cards
    all_cards.extend(generate_level_6_cards())   # 20 cards
    all_cards.extend(generate_level_7_cards())   # 45 cards
    all_cards.extend(generate_level_8_cards())   # 60 cards
    all_cards.extend(generate_level_9_cards())   # 50 cards
    all_cards.extend(generate_level_10_cards())  # 40 cards

    return all_cards


def seed_cards() -> None:
    """
    Seed cards table with all learning cards across 10 levels.

    Total: ~380 cards based on research-backed Spanish literacy pedagogy.
    """
    logger.info("Starting cards seed script")

    with Session(engine) as session:
        # Check if cards already exist
        existing_count = len(session.exec(select(Card)).all())

        if existing_count > 0:
            logger.warning(
                f"Cards table already has {existing_count} records. Skipping seed."
            )
            return

        # Generate all cards programmatically
        all_cards = generate_all_cards()

        # Insert cards
        for card_data in all_cards:
            card = Card(**card_data)
            session.add(card)
            logger.debug(f"Added card {card.id}: {card.content} ({card.content_type})")

        session.commit()
        logger.info(f"Successfully seeded {len(all_cards)} cards across 10 levels")

        # Log cards per level
        cards_by_level = {}
        for card_data in all_cards:
            level_id = card_data["level_id"]
            cards_by_level[level_id] = cards_by_level.get(level_id, 0) + 1

        for level_id in sorted(cards_by_level.keys()):
            logger.info(f"  Level {level_id}: {cards_by_level[level_id]} cards")


if __name__ == "__main__":
    try:
        seed_cards()
    except Exception as e:
        logger.error(f"Error seeding cards: {e}", exc_info=True)
        sys.exit(1)
