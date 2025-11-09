# Audio Generation Guide

This guide explains how to generate and upload audio files for cards using ElevenLabs TTS API.

## Quick Start

**Generate audio for all cards:**
```bash
cd backend
uv run python scripts/generate_and_update_audio.py
```

**Generate for a single card:**
```bash
uv run python scripts/generate_and_update_audio.py --card-id vowel_a_lower
```

**Generate only cards with incorrect URLs:**
```bash
uv run python scripts/generate_and_update_audio.py --only-incorrect
```

## Overview

The audio generation workflow:
1. Generates audio using ElevenLabs TTS (Spanish voice)
2. Uploads MP3 files to Supabase Storage (`audio-files` bucket)
3. Updates each card's `audio_url` in database automatically

Storage structure:
```
audio-files/
├── vowels/         # Level 1: Vowel sounds
├── syllables/      # Levels 2-3, 7-8: Syllable combinations
├── words/          # Levels 4-5, 7, 9-10: Complete words
└── proper/         # Level 6: Proper nouns
```

**Note on special characters:** Files with Spanish special characters (ñ, á, é, í, ó, ú) are automatically normalized to ASCII (ñ→n, á→a, etc.) for Supabase Storage compatibility. The audio still pronounces the original text correctly.

## Prerequisites

**1. Install dependencies:**
```bash
cd backend && uv sync
```

**2. Configure `.env`:**
```bash
ELEVEN_LABS_API_KEY=your-elevenlabs-api-key-here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here      # For storage access
```

## Usage

### Process All Cards
```bash
uv run python scripts/generate_and_update_audio.py
```

**What happens:**
- Generates audio using ElevenLabs TTS (Spanish voice ID: `zTGs6vubfUHrD7hJ5Btq`)
- Saves MP3 files locally to `backend/audio_files/`
- Uploads to Supabase Storage bucket `audio-files`
- Updates each card's `audio_url` in database automatically
- Skips cards that already have correct HTTPS URLs (resumable)

**Time:** ~5-10 minutes for all ~363 cards

### Process Only Incorrect URLs
```bash
uv run python scripts/generate_and_update_audio.py --only-incorrect
```

Processes only cards with:
- NULL audio_url
- Incorrect URLs (not starting with `https://`)

### Process Single Card
```bash
uv run python scripts/generate_and_update_audio.py --card-id vowel_a_lower
```

### Force Regenerate
```bash
uv run python scripts/generate_and_update_audio.py --force
```

Forces regeneration even if audio files already exist locally.

## Utility Scripts

### Check Card URLs
```bash
uv run python scripts/check_card_urls.py
```

Displays a report showing which cards have correct/incorrect/null URLs.

### Upload Only (No Generation)
```bash
uv run python scripts/upload_audio.py
```

Uploads existing local audio files to Supabase without generating new ones.

## Troubleshooting

**ElevenLabs API key error:**
```bash
# Verify key is loaded
uv run python -c "from app.config import settings; print(settings.eleven_labs_api_key[:10] + '...')"
```

**Supabase connection error:**
```bash
# Check credentials
uv run python -c "from app.config import settings; print(settings.supabase_url)"
```

**Invalid key error (special characters):**
The script automatically normalizes Spanish special characters. If you still see this error, check the logs for the specific filename.

**Force regenerate all files:**
```bash
rm -rf backend/audio_files/
uv run python scripts/generate_and_update_audio.py --force
```

**Rate limiting:** Re-run the script - it resumes from where it stopped.

## Common Tasks

**Regenerate single card:**
```bash
uv run python scripts/generate_and_update_audio.py --card-id vowel_a_lower --force
```

**Fix cards with incorrect URLs:**
```bash
uv run python scripts/generate_and_update_audio.py --only-incorrect
```

**Add audio for new cards:**
```bash
# After adding cards to database
uv run python scripts/generate_and_update_audio.py
# Only processes cards without audio_url or missing files
```

## Configuration

**Current settings:**
- Voice ID: `zTGs6vubfUHrD7hJ5Btq` (Spanish voice)
- Model: `eleven_turbo_v2_5`
- Format: `mp3_44100_128`
- Language: Spanish (`es`)
- Speed: 0.8
- Stability: 0.9
- Prompt format: `"{content}" <break time="0.5s" />`

**To customize:** Edit `backend/scripts/generate_and_update_audio.py` lines 44-54

**Storage:**
- Format: MP3 (44.1kHz, 128kbps)
- Size: ~20-30 KB per file
- Total: ~10-15 MB for all cards

## Production Checklist

- [x] Generate audio for all cards
- [x] Fix cards with special characters
- [ ] Verify bucket is public in Supabase Dashboard
- [ ] Test audio playback in frontend
- [ ] Test on mobile devices

## Resources

- [ElevenLabs API Documentation](https://elevenlabs.io/docs)
- [Supabase Storage Documentation](https://supabase.com/docs/guides/storage)
