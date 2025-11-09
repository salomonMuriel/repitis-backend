"""Generate audio files, upload to Supabase, and update card URLs in database."""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import Session, select

from app.config import settings, setup_logging
from app.database import engine
from app.models import Card
from elevenlabs import ElevenLabs
from scripts.upload_audio import (
    ensure_bucket_exists,
    initialize_supabase,
    upload_file,
    BUCKET_NAME,
)

setup_logging()
logger = logging.getLogger(__name__)


def normalize_filename(text: str) -> str:
    """
    Normalize Spanish special characters for filenames.

    Replaces:
    - Accented vowels (á, é, í, ó, ú) with base form (a, e, i, o, u)
    - ñ with n

    Args:
        text: Text to normalize

    Returns:
        Normalized text safe for filenames
    """
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'ñ': 'n', 'Ñ': 'N'
    }

    result = text
    for char, replacement in replacements.items():
        result = result.replace(char, replacement)

    return result


def generate_audio_for_content(client: ElevenLabs, content: str, output_path: Path) -> bool:
    """
    Generate audio for content using Eleven Labs TTS API.

    Args:
        client: Eleven Labs API client
        content: Text content to convert to speech
        output_path: Path to save the audio file (MP3 format)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Format text with quotes and break time for better pronunciation
        formatted_text = f'"{content}" <break time="0.5s" />'

        # Generate audio using Eleven Labs TTS with Spanish voice
        audio_generator = client.text_to_speech.convert(
            voice_id="zTGs6vubfUHrD7hJ5Btq",  # Spanish voice
            output_format="mp3_44100_128",
            text=formatted_text,
            model_id="eleven_turbo_v2_5",
            language_code="es",  # Spanish
            voice_settings={
                "stability": 0.9,
                "speed": 0.8
            }
        )

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write audio bytes to file
        with open(output_path, "wb") as f:
            for chunk in audio_generator:
                f.write(chunk)

        logger.debug(f"Generated audio: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to generate audio for '{content}': {e}")
        return False


def get_audio_url(path: str) -> str:
    """
    Generate Supabase Storage URL for audio file.

    Args:
        path: Relative path within bucket (e.g., 'vowels/a.mp3')

    Returns:
        Full Supabase Storage URL
    """
    return f"{settings.supabase_url}/storage/v1/object/public/{BUCKET_NAME}/{path}"


def generate_upload_and_update(
    card_id: str | None = None,
    output_dir: Path | None = None,
    force_regenerate: bool = False,
    only_incorrect: bool = False,
) -> None:
    """
    Generate audio for cards, upload to Supabase, and update database URLs.

    Args:
        card_id: Specific card ID to process (None = process all cards)
        output_dir: Directory to save audio files (default: backend/audio_files/)
        force_regenerate: If True, regenerate even if file exists locally
        only_incorrect: If True, only process cards with incorrect URLs (not starting with https://)
    """
    logger.info("Starting audio generation, upload, and database update workflow")

    # Set default output directory
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "audio_files"

    # Initialize clients
    try:
        elevenlabs_client = ElevenLabs(api_key=settings.eleven_labs_api_key)
        logger.info("Eleven Labs API client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Eleven Labs client: {e}")
        sys.exit(1)

    supabase_client = initialize_supabase()
    ensure_bucket_exists(supabase_client)

    # Get cards from database
    with Session(engine) as session:
        if card_id:
            # Process single card
            card = session.get(Card, card_id)
            if not card:
                logger.error(f"Card '{card_id}' not found in database")
                sys.exit(1)
            cards = [card]
            logger.info(f"Processing single card: {card_id}")
        else:
            # Build query based on filters
            statement = select(Card).order_by(Card.level_id, Card.id)

            if only_incorrect:
                # Filter for cards with incorrect URLs (not starting with https://)
                statement = statement.where(
                    (Card.audio_url == None) | (~Card.audio_url.startswith('https://'))
                )

            cards = session.exec(statement).all()

            if only_incorrect:
                logger.info(f"Processing {len(cards)} cards with incorrect URLs")
            else:
                logger.info(f"Processing all {len(cards)} cards")

        # Track statistics
        success_count = 0
        failed_count = 0
        skipped_count = 0

        for i, card in enumerate(cards, 1):
            content = card.content
            logger.info(f"\n[{i}/{len(cards)}] Processing card '{card.id}': {content}")

            # Determine file paths based on card type and content
            # Normalize filename to remove Spanish special characters
            normalized_content = normalize_filename(content)

            if card.content_type == "letter" or card.content_type == "syllable":
                # Use content type as subfolder
                if "vowel" in card.id:
                    subfolder = "vowels"
                elif card.content_type == "syllable":
                    subfolder = "syllables"
                else:
                    subfolder = "letters"
                filename = f"{normalized_content}.mp3"
            elif card.content_type == "proper_noun":
                subfolder = "proper"
                filename = f"{normalized_content.lower()}.mp3"
            else:  # word
                subfolder = "words"
                filename = f"{normalized_content}.mp3"

            local_path = output_dir / subfolder / filename
            remote_path = f"{subfolder}/{filename}"
            new_audio_url = get_audio_url(remote_path)

            # Check if file exists locally
            if local_path.exists() and not force_regenerate:
                logger.debug(f"Audio file already exists locally: {local_path}")
            else:
                # Generate audio
                logger.info(f"Generating audio for: {content}")
                if not generate_audio_for_content(elevenlabs_client, content, local_path):
                    logger.error(f"Failed to generate audio for card {card.id}")
                    failed_count += 1
                    continue
                logger.info(f"Generated: {local_path} ({local_path.stat().st_size} bytes)")

            # Verify file exists before uploading
            if not local_path.exists():
                logger.error(f"Audio file does not exist: {local_path}")
                failed_count += 1
                continue

            # Upload to Supabase
            logger.info(f"Uploading to Supabase: {remote_path}")
            if not upload_file(supabase_client, local_path, remote_path):
                logger.error(f"Failed to upload audio for card {card.id}")
                failed_count += 1
                continue

            # Update card's audio_url in database
            card.audio_url = new_audio_url
            session.add(card)
            session.commit()
            session.refresh(card)

            logger.info(f"✅ Updated card audio_url: {card.audio_url}")
            success_count += 1

        # Log summary
        logger.info("\n" + "=" * 60)
        logger.info("Audio generation and update complete!")
        logger.info(f"  Success: {success_count}")
        logger.info(f"  Failed:  {failed_count}")
        logger.info(f"  Skipped: {skipped_count}")
        logger.info(f"  Total:   {len(cards)}")
        logger.info("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate audio, upload to Supabase, and update database"
    )
    parser.add_argument(
        "--card-id",
        type=str,
        help="Process only a specific card by ID (e.g., 'vowel_a_lower')",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regenerate audio even if file exists locally",
    )
    parser.add_argument(
        "--only-incorrect",
        action="store_true",
        help="Only process cards with incorrect URLs (not starting with https://)",
    )

    args = parser.parse_args()

    try:
        generate_upload_and_update(
            card_id=args.card_id,
            force_regenerate=args.force,
            only_incorrect=args.only_incorrect,
        )
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
