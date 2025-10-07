#!/usr/bin/env python3
"""
regenerate_summaries.py

Regenerate all existing summaries based on transcriptions.
Useful after updating prompt.md or switching models.

Usage:
  python regenerate_summaries.py [--dry-run] [--model MODEL] [--no-publish]
"""

import sys
import argparse
import subprocess
from pathlib import Path
from typing import List
import os

# Import functions from process.py
from process import (
    load_prompt,
    load_transcription,
    process_transcription,
    save_summary,
    git_publish
)

# Import utilities
from utils import parse_filename_details, get_summary_filepath


def find_all_transcriptions(transcriptions_dir: Path) -> List[Path]:
    """Find all .txt files in transcriptions directory."""
    if not transcriptions_dir.exists():
        print(f"❌ Transcriptions directory {transcriptions_dir} does not exist.")
        return []

    txt_files = sorted(transcriptions_dir.glob("*.txt"))
    print(f"Found {len(txt_files)} transcriptions in {transcriptions_dir}")
    return txt_files


def clear_existing_summaries(forelesninger_dir: Path, dry_run: bool = False):
    """Remove all existing .md files from forelesninger directory."""
    if not forelesninger_dir.exists():
        print(f"Forelesninger directory {forelesninger_dir} does not exist.")
        return

    md_files = []
    for course_dir in forelesninger_dir.iterdir():
        if course_dir.is_dir():
            for month_dir in course_dir.iterdir():
                if month_dir.is_dir():
                    md_files.extend(month_dir.glob("*.md"))

    print(f"\nFound {len(md_files)} existing summaries to delete")

    if dry_run:
        print("\n🔍 DRY RUN - Would delete:")
        for md_file in md_files:
            print(f"  ❌ {md_file.relative_to(forelesninger_dir.parent)}")
        return

    for md_file in md_files:
        md_file.unlink()
        print(f"  ❌ Deleted: {md_file.relative_to(forelesninger_dir.parent)}")


def regenerate_summary(
    transcript_path: Path,
    model: str,
    temperature: float,
    dry_run: bool = False
) -> Path:
    """Regenerate a single summary."""
    # Get the expected summary filepath using the same logic as process.py
    summary_file = Path(get_summary_filepath(str(transcript_path)))

    # Verify we could parse the filename
    details = parse_filename_details(str(transcript_path))
    if not details:
        print(f"⚠️  Could not parse filename: {transcript_path.name}")
        return None

    if dry_run:
        print(f"  ✅ Would regenerate: {summary_file}")
        return summary_file

    print(f"\n{'='*60}")
    print(f"📝 Processing: {transcript_path.name}")
    print(f"{'='*60}")

    # Load prompt and transcription
    system_prompt = load_prompt()
    transcription = load_transcription(str(transcript_path))

    # Process with AI
    summary = process_transcription(
        transcription,
        system_prompt,
        model=model,
        temperature=temperature
    )

    # Save result
    result_path = save_summary(summary, str(transcript_path))

    return Path(result_path)


def main():
    parser = argparse.ArgumentParser(
        description="Regenerate all lecture summaries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (see what would be done)
  python regenerate_summaries.py --dry-run

  # Regenerate all with default model
  python regenerate_summaries.py

  # Use different model
  python regenerate_summaries.py --model anthropic/claude-3.5-sonnet

  # Skip git publish
  python regenerate_summaries.py --no-publish
        """
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it"
    )
    parser.add_argument(
        "--model",
        default="anthropic/claude-3.5-sonnet",
        help="Model to use (default: anthropic/claude-3.5-sonnet)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature 0-1 (default: 0.2)"
    )
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Skip Git publish step"
    )

    args = parser.parse_args()

    script_dir = Path.cwd()
    transcriptions_dir = script_dir / "transcriptions"
    forelesninger_dir = script_dir / "forelesninger"

    print("\n" + "="*60)
    print("🔄 ALTS REGENERATE SUMMARIES")
    print("="*60)
    print(f"Transcriptions: {transcriptions_dir}")
    print(f"Forelesninger:  {forelesninger_dir}")
    print(f"Model:          {args.model}")
    print(f"Temperature:    {args.temperature}")
    print(f"Dry run:        {args.dry_run}")
    print(f"Git publish:    {not args.no_publish}")
    print("="*60)

    # 1. Find all transcriptions
    print("\n📂 Step 1: Finding transcriptions...")
    transcript_files = find_all_transcriptions(transcriptions_dir)
    if not transcript_files:
        print("❌ No transcriptions found. Exiting.")
        return

    # 2. Clear existing summaries
    print("\n🗑️  Step 2: Clearing existing summaries...")
    clear_existing_summaries(forelesninger_dir, dry_run=args.dry_run)

    if args.dry_run:
        print("\n" + "="*60)
        print("🔍 DRY RUN COMPLETE")
        print("="*60)
        print(f"Would process {len(transcript_files)} transcriptions")
        print("\nRun without --dry-run to actually regenerate summaries")
        return

    # 3. Regenerate all summaries
    print(f"\n🤖 Step 3: Regenerating {len(transcript_files)} summaries...")
    generated_files = []

    for i, transcript_path in enumerate(transcript_files, 1):
        print(f"\n[{i}/{len(transcript_files)}]")
        try:
            summary_path = regenerate_summary(
                transcript_path,
                model=args.model,
                temperature=args.temperature,
                dry_run=False
            )
            if summary_path:
                generated_files.append(summary_path)
        except Exception as e:
            print(f"❌ ERROR processing {transcript_path.name}: {e}")
            continue

    # 4. Git commit and push
    if not args.no_publish and generated_files:
        print(f"\n📤 Step 4: Publishing to Git...")

        # Check if git repo
        try:
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                check=True,
                capture_output=True,
                cwd=script_dir
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  Not a Git repository. Skipping git publish.")
            print("   To enable: git init && git remote add origin <url>")
        else:
            # Add all forelesninger files
            try:
                subprocess.run(
                    ["git", "add", "forelesninger/"],
                    check=True,
                    cwd=script_dir
                )

                # Check if there are changes
                result = subprocess.run(
                    ["git", "diff", "--cached", "--quiet"],
                    cwd=script_dir
                )

                if result.returncode != 0:  # There are changes
                    commit_msg = f"ALTS: Regenerated {len(generated_files)} summaries"
                    subprocess.run(
                        ["git", "commit", "-m", commit_msg],
                        check=True,
                        cwd=script_dir
                    )
                    print(f"✓ Committed: {commit_msg}")

                    # Push
                    try:
                        subprocess.run(
                            ["git", "push"],
                            check=True,
                            cwd=script_dir
                        )
                        print("✓ Pushed to remote repository")
                    except subprocess.CalledProcessError as e:
                        print(f"⚠️  Git push failed")
                        print("   You may need to push manually")
                else:
                    print("ℹ️  No changes to commit")

            except subprocess.CalledProcessError as e:
                print(f"❌ Git operation failed: {e}")

    # Final summary
    print("\n" + "="*60)
    print("✅ REGENERATION COMPLETE")
    print("="*60)
    print(f"Processed:     {len(transcript_files)} transcriptions")
    print(f"Generated:     {len(generated_files)} summaries")
    if args.no_publish:
        print("Git publish:   Skipped (--no-publish)")
    print("\n🎉 All done!")


if __name__ == "__main__":
    main()
