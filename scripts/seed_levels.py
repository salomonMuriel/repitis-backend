"""Seed script for levels table."""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import Session, select

from app.config import settings, setup_logging
from app.database import engine
from app.models import Level

setup_logging()
logger = logging.getLogger(__name__)

# Level data (10 progressive difficulty levels)
# Based on research-backed Spanish literacy pedagogy (see LEVELS.md)
LEVELS_DATA = [
    {
        "id": 1,
        "name": "Vocales",
        "description": "Reconocimiento de sonidos y formas de las 5 vocales",
        "mastery_threshold": 0.8,
    },
    {
        "id": 2,
        "name": "Sílabas Fáciles",
        "description": "Primeras combinaciones consonante-vocal con m, n, p, s, l",
        "mastery_threshold": 0.8,
    },
    {
        "id": 3,
        "name": "Todas las Sílabas Simples",
        "description": "Completa todas las sílabas abiertas básicas sin consonantes compuestas",
        "mastery_threshold": 0.8,
    },
    {
        "id": 4,
        "name": "Palabras de Dos Sílabas",
        "description": "Combina sílabas en palabras reales usando solo consonantes simples",
        "mastery_threshold": 0.8,
    },
    {
        "id": 5,
        "name": "Sílabas Cerradas",
        "description": "Aprende patrones de sílabas no abiertas (VC, CVC): sol, pan, mar",
        "mastery_threshold": 0.8,
    },
    {
        "id": 6,
        "name": "Nombres Propios y Mayúsculas",
        "description": "Uso de mayúsculas en contexto significativo: nombres y lugares",
        "mastery_threshold": 0.8,
    },
    {
        "id": 7,
        "name": "Dígrafos",
        "description": "Dos letras que hacen un sonido: ch, ll, rr",
        "mastery_threshold": 0.8,
    },
    {
        "id": 8,
        "name": "Grupos Consonánticos",
        "description": "Combina dos consonantes juntas: pr, br, tr, pl, bl, cl, fl, gr, dr, cr, fr",
        "mastery_threshold": 0.8,
    },
    {
        "id": 9,
        "name": "Palabras de Tres o Más Sílabas",
        "description": "Lectura multi-silábica extendida, síntesis de todas las habilidades",
        "mastery_threshold": 0.8,
    },
    {
        "id": 10,
        "name": "Diptongos y Patrones Avanzados",
        "description": "Combinaciones vocálicas complejas y reglas ortográficas",
        "mastery_threshold": 0.8,
    },
]


def seed_levels() -> None:
    """Seed levels table with 10 difficulty levels."""
    logger.info("Starting levels seed script")

    with Session(engine) as session:
        # Check if levels already exist
        existing_count = len(session.exec(select(Level)).all())

        if existing_count > 0:
            logger.warning(
                f"Levels table already has {existing_count} records. Skipping seed."
            )
            return

        # Insert levels
        for level_data in LEVELS_DATA:
            level = Level(**level_data)
            session.add(level)
            logger.info(f"Added level {level.id}: {level.name}")

        session.commit()
        logger.info(f"Successfully seeded {len(LEVELS_DATA)} levels")


if __name__ == "__main__":
    try:
        seed_levels()
    except Exception as e:
        logger.error(f"Error seeding levels: {e}", exc_info=True)
        sys.exit(1)
