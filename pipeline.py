#!/usr/bin/env python3
"""
ALTS Pipeline - Automated Lecture Transcription & Summary
Komplett workflow: Download → Transcribe → Summarize
"""

import argparse
import sys
import os

# Import run functions from other scripts
from download import run_download, get_expected_filename, parse_filename_to_mp3
from transcribe import run_transcribe
from process import run_process

# Import utils
from utils import get_language_for_course, extract_course_code_from_filename, validate_git_setup, check_file_on_github, get_summary_filepath

def pipeline(url, language, model, temperature, no_publish):
    """
    Run complete pipeline: Download → Transcribe → Summarize
    Sjekker om filer allerede finnes på GitHub/lokalt før de genereres.

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

    # Determine expected file paths from URL
    print("\n🔍 Sjekker forventede filnavn fra URL...")
    expected_filename = get_expected_filename(url)
    if not expected_filename:
        print("❌ Kunne ikke hente forventet filnavn fra URL")
        sys.exit(1)

    expected_mp3 = parse_filename_to_mp3(expected_filename)
    mp3_path = os.path.join("downloads", expected_mp3)
    transcript_path = mp3_path.replace("downloads/", "transcriptions/").replace(".mp3", ".txt")
    summary_path = get_summary_filepath(transcript_path)

    print(f"  Forventet MP3:        {mp3_path}")
    print(f"  Forventet transkripsjon: {transcript_path}")
    print(f"  Forventet sammendrag:    {summary_path}")

    # Check if summary already exists on GitHub
    print("\n🔍 Sjekker om sammendrag allerede finnes på GitHub...")
    if check_file_on_github(summary_path):
        print(f"\n✅ Sammendrag finnes allerede på GitHub!")
        print(f"   {summary_path}")
        print("\n🎉 Alt er allerede ferdig - ingenting å gjøre!")

        # Print summary
        print("\n" + "="*60)
        print("📋 PIPELINE STATUS: ALREADY COMPLETE")
        print("="*60)
        print("\nEksisterende filer:")
        if os.path.exists(mp3_path):
            print(f"  🎵 Audio:       {mp3_path}")
        if os.path.exists(transcript_path):
            print(f"  📝 Transcript:  {transcript_path}")
        print(f"  📊 Summary:     {summary_path} (på GitHub)")
        print("\n" + "="*60)
        return

    # Validate Git setup before starting (only if not --no-publish)
    if not no_publish:
        git_status = validate_git_setup(verbose=True)
        if not git_status["is_git_repo"] or not git_status["can_commit"]:
            print("\n⚠️  Git er ikke korrekt konfigurert for publisering")
            print("   Pipeline vil kjøre, men Git-publisering vil bli hoppet over")
            print("   Bruk --no-publish for å unngå denne meldingen")
            response = input("\nFortsette? [Y/n]: ")
            if response.lower() == 'n':
                sys.exit(0)

    # Step 1: Download and convert to MP3
    print(f"\n📥 STEP 1/3: Download")
    mp3_file = run_download(url)
    if not mp3_file:
        print("❌ Download failed")
        sys.exit(1)

    # Auto-detect language if not specified
    if not language:
        filename = os.path.basename(mp3_file)
        course_code = extract_course_code_from_filename(filename)
        if course_code:
            language = get_language_for_course(course_code)
            print(f"  Language: {language} (auto-detected from {course_code})")
        else:
            language = "en"  # Default fallback
            print(f"  Language: {language} (default)")

    # Step 2: Transcribe with WhisperX
    print(f"\n📝 STEP 2/3: Transcription")
    transcript_file = run_transcribe(
        audio_file=mp3_file,
        model_size="large-v3", # Or make this a parameter
        language=language,
        hf_token=os.environ.get("HF_TOKEN") # Or make this a parameter
    )
    if not transcript_file:
        print("❌ Transcription failed")
        sys.exit(1)

    # Step 3: Generate summary with OpenRouter
    print(f"\n🤖 STEP 3/3: AI Summary")
    summary_file = run_process(
        transcription_file=transcript_file,
        model=model,
        temperature=temperature,
        no_publish=no_publish
    )
    if not summary_file:
        print("❌ Summary generation failed")
        sys.exit(1)

    # Final summary
    print("\n" + "="*60)
    print("✅ PIPELINE COMPLETE!")
    print("="*60)
    print(f"\n  🎵 Audio:      {mp3_file}")
    print(f"  📝 Transcript: {transcript_file}")
    print(f"  📊 Summary:    {summary_file}")
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

    parser.add_argument("url", nargs="?", help="Panopto lecture URL")
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

    # Ask for URL if not provided
    url = args.url
    if not url:
        url = input("Enter the Panopto lecture URL: ")
        if not url:
            print("Error: URL is required")
            sys.exit(1)

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
        url,
        language=args.language,
        model=args.model,
        temperature=args.temperature,
        no_publish=args.no_publish
    )

if __name__ == "__main__":
    main()
