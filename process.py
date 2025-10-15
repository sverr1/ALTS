import os
import sys
import argparse
import subprocess
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from utils import get_summary_filepath, parse_filename_details, validate_git_setup

# Chunking configuration for large transcriptions
# 3-hour lecture ~36k tokens. 150k chars ~ 37.5k tokens.
CHUNK_SIZE = 150_000
CHUNK_OVERLAP = 5_000

def load_prompt():
    """Load the processing prompt from prompt.md"""
    prompt_path = "prompt.md"
    if not os.path.exists(prompt_path):
        print(f"Error: {prompt_path} not found")
        sys.exit(1)

    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

def load_transcription(transcription_file):
    """Load transcription from file"""
    if not os.path.exists(transcription_file):
        print(f"Error: Transcription file not found: {transcription_file}")
        sys.exit(1)

    with open(transcription_file, 'r', encoding='utf-8') as f:
        return f.read()

def process_transcription(transcription_text, system_prompt, model="anthropic/claude-3.5-sonnet", temperature=0.2):
    """
    Send transcription to OpenRouter for processing with automatic chunking for large files.

    Args:
        transcription_text: The raw transcription text
        system_prompt: System prompt from prompt.md
        model: Model to use (default: claude-3.5-sonnet via OpenRouter)
        temperature: Sampling temperature (default: 0.2 for focused output)

    Returns:
        Processed summary as markdown text
    """
    # Load API key from .env
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        print("Error: OPENROUTER_API_KEY not found in .env file")
        print("Create a .env file with: OPENROUTER_API_KEY=your_key_here")
        sys.exit(1)

    # Initialize OpenRouter client (compatible with OpenAI SDK)
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

    print(f"  Processing with {model}...", end='', flush=True)

    def get_summary_for_text(text: str, is_final_summary: bool = False, show_progress: bool = False) -> str:
        """Helper function to get summary for a single text chunk."""
        system_msg = (
            "You are an expert summarizer. Create a detailed, structured summary of the following lecture transcript. Use Markdown formatting."
            if not is_final_summary else
            "You are an expert synthesizer. Combine the following partial summaries into a single, coherent, and detailed lecture summary. Remove redundancies. Use Markdown formatting."
        )

        user_content = f"{system_prompt}\n\n---\n\nTRANSCRIPT:\n\n{text}" if not is_final_summary else text

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_content}
                ],
                temperature=temperature,
                max_tokens=16000
            )
            result = response.choices[0].message.content or ""
            if show_progress:
                if not is_final_summary:
                    print(f"\n    ✓ Chunk processed ({response.usage.total_tokens} tokens)")
                else:
                    print(f"\n    ✓ Final synthesis ({response.usage.total_tokens} tokens)")
            return result
        except Exception as e:
            return f"Error during summarization: {e}"

    # Check if transcription is short enough for single request
    if len(transcription_text) <= CHUNK_SIZE:
        try:
            summary = get_summary_for_text(transcription_text)
            print(" ✓")
            return summary
        except Exception as e:
            print(f"\n  Error calling OpenRouter API: {e}")
            sys.exit(1)

    # Hierarchical summarization (chunking)
    print(f"\n  Large transcript ({len(transcription_text)} chars) - using chunking")
    chunks = []
    start = 0
    while start < len(transcription_text):
        end = start + CHUNK_SIZE
        chunks.append(transcription_text[start:end])
        start = end - CHUNK_OVERLAP

    print(f"  Processing {len(chunks)} chunks...")

    # Summarize each chunk
    partial_summaries = []
    for i, chunk in enumerate(chunks, 1):
        print(f"    Chunk {i}/{len(chunks)}...", end='', flush=True)
        summary = get_summary_for_text(chunk, show_progress=True)
        partial_summaries.append(f"### Summary of Part {i}\n\n{summary}")

    # Combine partial summaries into final summary
    print(f"  Synthesizing final summary...", end='', flush=True)
    final_summary_prompt = (
        f"{system_prompt}\n\n---\n\n"
        "Combine these partial summaries into one single, coherent summary:\n\n"
        + "\n\n---\n\n".join(partial_summaries)
    )

    try:
        final_summary = get_summary_for_text(final_summary_prompt, is_final_summary=True, show_progress=True)
        return final_summary
    except Exception as e:
        print(f"\n  Error during final synthesis: {e}")
        sys.exit(1)

def save_summary(summary_text, transcription_file):
    """
    Save processed summary to file in structured folder.

    Creates structure: forelesninger/EMNEKODE/YYYY_måned/EMNEKODE_YYYY-MM-DD.md
    """
    summary_file = get_summary_filepath(transcription_file)
    
    # Create directory if it doesn't exist
    summary_dir = os.path.dirname(summary_file)
    if not os.path.exists(summary_dir):
        os.makedirs(summary_dir)

    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary_text)

    print(f"  Saved to: {summary_file}")
    return summary_file

def git_publish(summary_file, emnekode, date_str):
    """
    Publish summary to Git repository with improved error handling.

    Args:
        summary_file: Path to the summary file
        emnekode: Course code (e.g., KJE101)
        date_str: Date string (e.g., 2025-10-03)
    """
    script_dir = Path.cwd()

    def run_git_cmd(*args):
        """Run a git command and return (returncode, stdout, stderr)"""
        try:
            process = subprocess.run(
                ["git"] + list(args),
                cwd=script_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            return process.returncode, process.stdout, process.stderr
        except FileNotFoundError:
            return 127, "", "git command not found"

    print(f"  Publishing to Git...", end='', flush=True)

    # Validate Git setup first
    git_status = validate_git_setup(verbose=False)

    if not git_status["is_git_repo"]:
        print(" (skipped - not a Git repo)")
        return

    if not git_status["can_commit"]:
        print(" (skipped - Git user not configured)")
        return

    # Add the summary file
    rc, _, err = run_git_cmd("add", summary_file)
    if rc != 0:
        print(f" (failed - {err})")
        return

    # Check if there are staged changes
    rc, _, _ = run_git_cmd("diff", "--cached", "--quiet")
    if rc == 0:
        print(" (no changes)")
        return

    # Commit
    commit_msg = f"ALTS: {emnekode} {date_str} - forelesningsnotat"
    rc, _, err = run_git_cmd("commit", "-m", commit_msg)
    if rc != 0:
        print(f" (failed - {err})")
        return

    # Push (only if remote is configured)
    if git_status["has_remote"]:
        rc, out, err = run_git_cmd("push")
        if rc != 0:
            print(f" (push failed - {err})")
        else:
            print(" ✓")
    else:
        print(" ✓ (local only)")

def run_process(transcription_file: str, model: str, temperature: float, no_publish: bool) -> str | None:
    """Runs the processing logic for a given transcription file.

    Args:
        transcription_file: Path to the transcription file.
        model: The AI model to use.
        temperature: The creativity temperature.
        no_publish: If True, skips the Git publish step.

    Returns:
        The path to the summary file, or None if failed or skipped.
    """
    summary_file = get_summary_filepath(transcription_file)

    if os.path.exists(summary_file):
        print(f"✓ Summary already exists: {summary_file}")
        print(f"  Skipping processing.")
        return summary_file

    system_prompt = load_prompt()
    transcription = load_transcription(transcription_file)

    summary = process_transcription(
        transcription,
        system_prompt,
        model=model,
        temperature=temperature
    )

    summary_file = save_summary(summary, transcription_file)

    if not no_publish:
        details = parse_filename_details(transcription_file, verbose=False)
        if details:
            git_publish(summary_file, details['course_code'], details['full_date'])

    return summary_file

def main():
    parser = argparse.ArgumentParser(
        description="Process lecture transcription with OpenRouter LLM"
    )
    parser.add_argument(
        "transcription_file",
        help="Path to transcription file (e.g., transcriptions/KJE101_2025-10-03.txt)"
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

    run_process(
        transcription_file=args.transcription_file,
        model=args.model,
        temperature=args.temperature,
        no_publish=args.no_publish
    )

if __name__ == "__main__":
    main()
