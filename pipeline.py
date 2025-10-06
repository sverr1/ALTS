#!/usr/bin/env python3
"""
ALTS Pipeline - Automated Lecture Transcription & Summary
Komplett workflow: Download → Transcribe → Summarize
"""

import argparse
import subprocess
import sys
import os
import glob
import re
from pathlib import Path
from utils import get_language_for_course, extract_course_code_from_filename

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"📌 {description}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, shell=True)

    if result.returncode != 0:
        print(f"\n❌ Error in step: {description}")
        sys.exit(1)

    return result.returncode == 0

def find_latest_file(pattern, directory="downloads"):
    """Find the most recently created file matching pattern"""
    files = glob.glob(f"{directory}/{pattern}")
    if not files:
        return None
    return max(files, key=os.path.getctime)

def pipeline(url, language=None, model="anthropic/claude-3.5-sonnet", temperature=0.2):
    """
    Run complete pipeline: Download → Transcribe → Summarize

    Args:
        url: Panopto URL
        language: Language code (en/no) or None for auto-detect
        model: OpenRouter model to use
        temperature: Creativity level (0.0-1.0, lower = more focused)
    """

    print("\n" + "="*60)
    print("🚀 ALTS PIPELINE START")
    print("="*60)
    print(f"URL:         {url}")
    if language:
        print(f"Language:    {language} (manual)")
    else:
        print(f"Language:    auto-detect from course code")
    print(f"Model:       {model}")
    print(f"Temperature: {temperature}")
    print("="*60)

    # Step 1: Download and convert to MP3
    run_command(
        f'python download.py "{url}"',
        "STEP 1/3: Downloading lecture from Panopto → MP3"
    )

    # Find the downloaded MP3 file
    mp3_file = find_latest_file("*.mp3")
    if not mp3_file:
        print("\n❌ Error: No MP3 file found after download")
        sys.exit(1)

    print(f"\n✓ Downloaded: {mp3_file}")

    # Auto-detect language if not specified
    if not language:
        filename = os.path.basename(mp3_file)
        course_code = extract_course_code_from_filename(filename)
        if course_code:
            language = get_language_for_course(course_code)
            print(f"\n🔍 Auto-detected language: '{language}' for course {course_code}")
        else:
            language = "en"  # Default fallback
            print(f"\n⚠️  Could not extract course code, defaulting to '{language}'")

    # Step 2: Transcribe with WhisperX
    run_command(
        f'python transcribe.py "{mp3_file}" --language {language}',
        "STEP 2/3: Transcribing with WhisperX"
    )

    # Find the transcription file
    base_name = os.path.splitext(os.path.basename(mp3_file))[0]
    transcript_file = f"transcriptions/{base_name}.txt"

    if not os.path.exists(transcript_file):
        print(f"\n❌ Error: Transcription file not found: {transcript_file}")
        sys.exit(1)

    print(f"\n✓ Transcribed: {transcript_file}")

    # Step 3: Generate summary with OpenRouter
    run_command(
        f'python process.py "{transcript_file}" --model {model} --temperature {temperature}',
        "STEP 3/3: Generating AI summary"
    )

    # Find the summary file - parse filename to get expected location
    basename = os.path.basename(transcript_file)
    match = re.match(r'([A-Z]+\d+)_(\d{4})-(\d{2})-(\d{2})\.txt', basename)

    if match:
        emnekode = match.group(1)
        year = match.group(2)
        month = int(match.group(3))
        day = match.group(4)

        # Norwegian month names
        months = {
            1: "januar", 2: "februar", 3: "mars", 4: "april",
            5: "mai", 6: "juni", 7: "juli", 8: "august",
            9: "september", 10: "oktober", 11: "november", 12: "desember"
        }
        month_name = months.get(month, "ukjent")

        summary_file = f"forelesninger/{emnekode}/{year}_{month_name}/{emnekode}_{year}-{match.group(3)}-{day}.md"
    else:
        # Fallback
        summary_file = transcript_file.replace(".txt", ".md")

    if not os.path.exists(summary_file):
        print(f"\n❌ Error: Summary file not found: {summary_file}")
        sys.exit(1)

    print(f"\n✓ Summary: {summary_file}")

    # Final summary
    print("\n" + "="*60)
    print("✅ PIPELINE COMPLETE!")
    print("="*60)
    print("\nGenerated files:")
    print(f"  🎵 Audio:       {mp3_file}")
    print(f"  📝 Transcript:  {transcript_file}")
    print(f"  📊 Summary:     {summary_file}")
    print("\n" + "="*60)

def main():
    parser = argparse.ArgumentParser(
        description="ALTS Complete Pipeline: Download → Transcribe → Summarize",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # English lecture (default)
  python pipeline.py "https://uis.cloud.panopto.eu/..."

  # Norwegian lecture
  python pipeline.py "https://uis.cloud.panopto.eu/..." --language no

  # Use different model
  python pipeline.py "https://url" --model openai/gpt-4o

  # Adjust creativity
  python pipeline.py "https://url" --temperature 0.5

Default model: Claude 3.5 Sonnet (best for academic summaries)
Default temperature: 0.2 (focused and precise)
        """
    )

    parser.add_argument(
        "url",
        help="Panopto lecture URL"
    )

    parser.add_argument(
        "--language",
        default=None,
        choices=["en", "no", "sv", "da", "de", "fr", "es"],
        help="Lecture language (default: auto-detect from course code)"
    )

    parser.add_argument(
        "--model",
        default="anthropic/claude-3.5-sonnet",
        help="OpenRouter model (default: anthropic/claude-3.5-sonnet)"
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature 0.0-1.0 (default: 0.2 for focused output)"
    )

    args = parser.parse_args()

    # Validate temperature
    if not 0.0 <= args.temperature <= 1.0:
        print("Error: Temperature must be between 0.0 and 1.0")
        sys.exit(1)

    # Check if .env exists
    if not os.path.exists(".env"):
        print("\n⚠️  Warning: .env file not found!")
        print("Create .env from .env.example and add your OPENROUTER_API_KEY")
        print("\nDo you want to continue anyway? (download and transcribe will still work)")
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            sys.exit(0)

    # Run pipeline
    pipeline(
        args.url,
        language=args.language,
        model=args.model,
        temperature=args.temperature
    )

if __name__ == "__main__":
    main()
