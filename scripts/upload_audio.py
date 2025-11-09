"""Upload generated audio files to Supabase Storage."""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from supabase import create_client, Client

from app.config import settings, setup_logging

setup_logging()
logger = logging.getLogger(__name__)


BUCKET_NAME = "audio-files"


def initialize_supabase() -> Client:
    """Initialize Supabase client with service role key."""
    try:
        client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_key  # Use service key for admin operations
        )
        logger.info("Supabase client initialized")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        sys.exit(1)


def ensure_bucket_exists(client: Client) -> None:
    """
    Ensure the audio-files bucket exists and is public.

    Args:
        client: Supabase client
    """
    try:
        # Try to get bucket info
        buckets = client.storage.list_buckets()
        bucket_exists = any(bucket.name == BUCKET_NAME for bucket in buckets)

        if bucket_exists:
            logger.info(f"Bucket '{BUCKET_NAME}' already exists")
        else:
            # Create bucket with public access
            client.storage.create_bucket(
                BUCKET_NAME,
                options={"public": True}
            )
            logger.info(f"Created bucket '{BUCKET_NAME}' with public access")

    except Exception as e:
        logger.error(f"Failed to ensure bucket exists: {e}")
        sys.exit(1)


def upload_file(client: Client, local_path: Path, remote_path: str) -> bool:
    """
    Upload a single file to Supabase Storage.

    Args:
        client: Supabase client
        local_path: Local file path
        remote_path: Remote path in bucket (e.g., 'vowels/a.wav')

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(local_path, "rb") as f:
            file_data = f.read()

        # Upload to Supabase Storage
        client.storage.from_(BUCKET_NAME).upload(
            remote_path,
            file_data,
            file_options={"content-type": "audio/wav", "upsert": "true"}
        )

        logger.debug(f"Uploaded: {remote_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to upload {local_path}: {e}")
        return False


def upload_all_audio(audio_dir: Path | None = None) -> None:
    """
    Upload all audio files from local directory to Supabase Storage.

    Args:
        audio_dir: Directory containing audio files (default: backend/audio_files/)
    """
    logger.info("Starting audio upload to Supabase Storage")

    # Set default audio directory
    if audio_dir is None:
        audio_dir = Path(__file__).parent.parent / "audio_files"

    if not audio_dir.exists():
        logger.error(f"Audio directory not found: {audio_dir}")
        logger.error("Please run generate_audio.py first to generate audio files")
        sys.exit(1)

    # Initialize Supabase
    client = initialize_supabase()

    # Ensure bucket exists
    ensure_bucket_exists(client)

    # Find all WAV files
    wav_files = list(audio_dir.rglob("*.wav"))

    if not wav_files:
        logger.warning(f"No WAV files found in {audio_dir}")
        return

    logger.info(f"Found {len(wav_files)} audio files to upload")

    # Track statistics
    success_count = 0
    failed_count = 0

    # Upload each file
    for i, local_path in enumerate(wav_files, 1):
        # Calculate remote path (relative to audio_dir)
        remote_path = str(local_path.relative_to(audio_dir)).replace("\\", "/")

        logger.info(f"[{i}/{len(wav_files)}] Uploading: {remote_path}")

        if upload_file(client, local_path, remote_path):
            success_count += 1
        else:
            failed_count += 1

    # Log summary
    logger.info("=" * 60)
    logger.info("Audio upload complete!")
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Failed:  {failed_count}")
    logger.info(f"  Total:   {len(wav_files)}")
    logger.info(f"  Bucket:  {BUCKET_NAME}")
    logger.info(f"  URL:     {settings.supabase_url}/storage/v1/object/public/{BUCKET_NAME}/")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        upload_all_audio()
    except Exception as e:
        logger.error(f"Error uploading audio: {e}", exc_info=True)
        sys.exit(1)
