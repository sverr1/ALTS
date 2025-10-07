# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ALTS (Automated Lecture Transcription & Summary System) is a complete pipeline for downloading lectures from Panopto, transcribing them with WhisperX (GPU-accelerated), and generating structured academic summaries using AI.

**Technology Stack:**
- Python 3.12
- WhisperX for GPU-accelerated transcription (CUDA required)
- OpenRouter API for AI summarization (Claude 3.5 Sonnet default)
- yt-dlp + ffmpeg for video download/conversion
- Git integration for automatic publishing

## Språk / Language

**VIKTIG:** All kommunikasjon og dokumentasjon i dette prosjektet skal være på norsk.
- Commit-meldinger: Norsk
- Kode-kommentarer: Norsk
- Dokumentasjon: Norsk
- Kommunikasjon med bruker: Norsk

Unntak: Tekniske termer og kodeeksempler kan bruke engelsk der det er naturlig.

## Common Commands

### Setup
```bash
# Activate virtual environment (always required)
source venv/bin/activate

# Create .env file (first time only)
cp .env.example .env
# Then edit .env to add OPENROUTER_API_KEY from https://openrouter.ai/
```

### Main Pipeline (Recommended)
```bash
# Complete workflow: Download → Transcribe → Summarize
python pipeline.py "https://panopto.url"

# With options
python pipeline.py "url" --language en              # Force language
python pipeline.py "url" --model openai/gpt-4o      # Different AI model
python pipeline.py "url" --temperature 0.5          # Adjust creativity
python pipeline.py "url" --no-publish               # Skip Git publishing
```

### Individual Steps
```bash
# 1. Download (creates MP3 in downloads/)
python download.py "https://panopto.url"

# 2. Transcribe (creates TXT in transcriptions/)
python transcribe.py downloads/KJE101_2025-10-03.mp3
python transcribe.py audio.mp3 --language en        # Force language

# 3. Summarize (creates MD in forelesninger/)
python process.py transcriptions/KJE101_2025-10-03.txt
python process.py transcript.txt --model openai/gpt-4o
python process.py transcript.txt --no-publish
```

### Batch Operations
```bash
# Regenerate all summaries (useful after editing prompt.md)
python regenerate_summaries.py --dry-run           # Preview changes
python regenerate_summaries.py                     # Execute
python regenerate_summaries.py --no-publish        # Skip Git
```

## Architecture

### Core Components

**pipeline.py** - Orchestrator that runs the complete workflow
- Calls `run_download()`, `run_transcribe()`, `run_process()` in sequence
- Handles language auto-detection from course codes
- Manages error propagation between stages

**download.py** - Panopto video downloader
- Uses yt-dlp with cookies.txt for authentication
- Automatically converts MP4 → MP3 (high quality, ~190 kbps) to save space
- Deletes original video after successful conversion
- Renames files to standard format: `EMNEKODE_YYYY-MM-DD.mp3`
- Strips lecture numbers (e.g., "FYS102-1" → "FYS102")

**transcribe.py** - WhisperX transcription with GPU acceleration
- Requires CUDA-capable NVIDIA GPU
- Uses large-v3 model by default (best quality)
- Automatic language detection or forced via `--language` flag
- Optional speaker diarization (requires HF_TOKEN environment variable)
- Alignment support for English; falls back gracefully for Norwegian/Swedish
- Output format: Plain text with timestamps `[start → end] text`

**process.py** - AI-powered summarization via OpenRouter
- Hierarchical chunking for transcripts >150k characters
- Chunks with 5k overlap to maintain context across boundaries
- Generates structured Markdown summaries based on prompt.md
- Automatic Git commit/push with descriptive messages
- Creates organized folder structure: `forelesninger/EMNEKODE/YYYY_måned/`

**utils.py** - Shared utilities
- `get_language_for_course()`: Maps course codes to languages (FYS/KJE→en, DAT/MAT→no)
- `extract_course_code_from_filename()`: Parses filenames to extract course codes
- `parse_filename_details()`: Extracts course code, year, month, day from filenames
- `get_summary_filepath()`: Constructs structured output paths for summaries

**regenerate_summaries.py** - Batch regeneration tool
- Processes all transcriptions in transcriptions/ directory
- Deletes existing summaries before regenerating (with dry-run preview)
- Single Git commit for all changes
- Useful when prompt.md is updated or switching AI models

### Data Flow

```
Panopto URL
    ↓ download.py
downloads/EMNEKODE_YYYY-MM-DD.mp3
    ↓ transcribe.py + WhisperX (GPU)
transcriptions/EMNEKODE_YYYY-MM-DD.txt
    ↓ process.py + OpenRouter API
forelesninger/EMNEKODE/YYYY_måned/EMNEKODE_YYYY-MM-DD.md
    ↓ git_publish()
Git commit + push
```

### File Naming Convention

**Downloads and transcriptions:** `EMNEKODE_YYYY-MM-DD.<ext>`
- Examples: `KJE101_2025-10-03.mp3`, `FYS102_2025-09-12.txt`

**Summaries:** `EMNEKODE_DD.MM.YY.md`
- Examples: `KJE101_03.10.25.md`, `FYS102_12.09.25.md`

**Rules:**
- Lecture numbers are automatically removed: `FYS102-1` → `FYS102`
- Date extracted from Panopto video title using regex: `(\d{2})\.(\d{2})\.(\d{4})`
- Summary format conversion handled by `utils.py:get_summary_filepath()`

### Language Auto-Detection

The system automatically determines lecture language from course codes:
- **English courses:** FYS (physics), KJE (chemistry)
- **Norwegian courses:** DAT (computer science), MAT (mathematics)
- **Default:** English (safer for mixed content)

Logic in `utils.py:get_language_for_course()`. Can be overridden with `--language` flag.

### Large Transcription Handling

For transcripts >150k characters (~3-hour lectures):
1. Split into chunks of 150k chars with 5k overlap
2. Summarize each chunk independently
3. Combine partial summaries into final synthesis

This hierarchical approach prevents context loss and API token limits.

### Git Integration

`process.py:git_publish()` automatically:
1. Checks if directory is a Git repository
2. Stages summary files
3. Commits with message: `ALTS: {emnekode} {date} - forelesningsnotat`
4. Pushes to remote (if configured)
5. Gracefully handles missing Git setup

Disable with `--no-publish` flag.

## Important Implementation Details

### Filename Parsing
- `download.py:rename_file()` uses regex `^([A-Z]+\d+)` to extract clean course codes
- `utils.py:parse_filename_details()` validates format and extracts structured data
- Always check if parsing returns None before using results

### WhisperX Quirks
- Alignment only works for English; Norwegian/Swedish skip alignment gracefully
- Speaker diarization requires HuggingFace token in HF_TOKEN env var
- Model must be loaded on GPU ("cuda" device) - no CPU fallback
- Memory cleanup after each stage (`gc.collect()`, `torch.cuda.empty_cache()`)

### OpenRouter API
- Uses OpenAI-compatible client: `OpenAI(base_url="https://openrouter.ai/api/v1")`
- Temperature default: 0.2 (focused, deterministic - good for academic content)
- Max tokens: 16000 per request
- Token usage tracked and logged during processing

### prompt.md Structure
The system prompt in `prompt.md` defines:
- Subject-specific formatting rules (LaTeX for math, Python for CS)
- Output structure (summary, key concepts, formulas, Cornell questions)
- Quality requirements and final checklist

When editing prompt.md, use `regenerate_summaries.py` to reprocess all lectures.

## Dependencies

### System Requirements
- **ffmpeg** - Audio/video conversion (install via system package manager)
- **yt-dlp** - Panopto downloads (install via system package manager)
- **NVIDIA GPU** with CUDA support (for WhisperX transcription)

### Python Packages (in venv)
- whisperx - GPU-accelerated transcription
- torch, torchaudio - PyTorch with CUDA
- nvidia-cublas-cu12, nvidia-cudnn-cu12 - CUDA libraries
- openai - OpenRouter API client
- python-dotenv - Environment variable management

### Configuration Files
- `.env` - Contains OPENROUTER_API_KEY (never commit!)
- `cookies.txt` - Panopto authentication cookies (never commit!)
- Both are in `.gitignore`

## Error Handling

### Known Issues & Warnings

**"No default align-model for language: sv/no"**
- Expected for Norwegian/Swedish - alignment is skipped, transcription continues

**"Library libcublas.so.12 is not found" or cudnn errors**
- CUDA libraries (cublas, cudnn) are installed in venv but need LD_LIBRARY_PATH
- Auto-fixed by venv/bin/activate which sets LD_LIBRARY_PATH
- If error persists: deactivate and re-activate venv
- Verify: `echo $LD_LIBRARY_PATH` should include nvidia/cublas/lib and nvidia/cudnn/lib paths

**"OPENROUTER_API_KEY not found"**
- Create .env file from .env.example
- Add API key from https://openrouter.ai/

**Download fails with authentication error**
- cookies.txt is outdated
- Re-export cookies from browser while logged into Panopto

### Function Return Values

All `run_*()` functions return:
- Path to output file on success (str)
- `None` on failure
- Check return value before proceeding to next stage

### File Existence Checks

Scripts skip processing if output already exists:
- `download.py` checks for existing MP3
- `transcribe.py` checks for existing TXT
- `process.py` checks for existing MD

Delete existing files to force regeneration, or use `regenerate_summaries.py --dry-run` to preview.

## Development Tips

### Testing Individual Stages
```bash
# Test download only
python download.py "url"

# Test transcription with existing audio
python transcribe.py downloads/existing.mp3 --language en

# Test summarization with existing transcript
python process.py transcriptions/existing.txt --no-publish
```

### Debugging Git Issues
```bash
# Check if Git repo exists
git rev-parse --is-inside-work-tree

# View recent ALTS commits
git log --grep="ALTS:" --oneline

# Manual commit if auto-publish fails
git add forelesninger/
git commit -m "ALTS: Manual commit"
git push
```

### Monitoring GPU Usage
WhisperX uses significant GPU memory. Monitor with:
```bash
watch -n 1 nvidia-smi
```

### Modifying the AI Prompt
1. Edit `prompt.md` with new instructions
2. Test on single transcript: `python process.py transcriptions/test.txt --no-publish`
3. If satisfied, regenerate all: `python regenerate_summaries.py`

## Course Code Conventions

The system recognizes these Norwegian university course codes:
- **DAT*** - Datateknologi (Computer Science)
- **MAT*** - Matematikk (Mathematics)
- **FYS*** - Fysikk (Physics)
- **KJE*** - Kjemi (Chemistry)

Course codes must be uppercase letters followed by digits. Lecture numbers (e.g., -1, -2) are automatically stripped.
