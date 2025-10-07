#!/usr/bin/env python3
"""
ALTS Pipeline - Automated Lecture Transcription & Summary
Komplett workflow: Download → Transcribe → Summarize
"""

import argparse
import sys
import os

# Import run functions from other scripts
from download import run_download
from transcribe import run_transcribe
from process import run_process

# Import utils
from utils import get_language_for_course, extract_course_code_from_filename

def pipeline(url, language, model, temperature, no_publish):
    """
    Run complete pipeline: Download → Transcribe → Summarize

    Args:
        url: Panopto URL
        language: Language code (en/no) or None for auto-detect
        model: OpenRouter model to use
        temperature: Creativity level (0.0-1.0, lower = more focused)
        no_publish: If True, skips the final Git publish step
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
    print(f"Publish:     {not no_publish}")
    print("="*60)

    # Step 1: Download and convert to MP3
    print(f"\n{'='*60}\n📌 STEP 1/3: Downloading lecture from Panopto → MP3\n{'='*60}")
    mp3_file = run_download(url)
    if not mp3_file:
        print("\n❌ Error in step: Download failed")
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
    print(f"\n{'='*60}\n📌 STEP 2/3: Transcribing with WhisperX\n{'='*60}")
    transcript_file = run_transcribe(
        audio_file=mp3_file,
        model_size="large-v3", # Or make this a parameter
        language=language,
        hf_token=os.environ.get("HF_TOKEN") # Or make this a parameter
    )
    if not transcript_file:
        print("\n❌ Error in step: Transcription failed")
        sys.exit(1)
    print(f"\n✓ Transcribed: {transcript_file}")

    # Step 3: Generate summary with OpenRouter
    print(f"\n{'='*60}\n📌 STEP 3/3: Generating AI summary\n{'='*60}")
    summary_file = run_process(
        transcription_file=transcript_file,
        model=model,
        temperature=temperature,
        no_publish=no_publish
    )
    if not summary_file:
        print("\n❌ Error in step: Summary generation failed")
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
  # Auto-detect language, publish to Git
  python pipeline.py "https://uis.cloud.panopto.eu/..."

  # Force Norwegian, skip publishing
  python pipeline.py "https://uis.cloud.panopto.eu/..." --language no --no-publish

  # Use a different model
  python pipeline.py "https://url" --model openai/gpt-4o

Default model: Claude 3.5 Sonnet
Default temperature: 0.2
        """
    )

    parser.add_argument("url", help="Panopto lecture URL")
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
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Skip the final Git publish step"
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
        temperature=args.temperature,
        no_publish=args.no_publish
    )

if __name__ == "__main__":
    main()
