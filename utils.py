"""
ALTS Utility Functions
Shared helper functions for language detection and course code parsing
"""
import os
import re
import subprocess
from pathlib import Path

def get_language_for_course(course_code: str) -> str:
    """
    Auto-detect language based on course code.

    Args:
        course_code: Course code (e.g., FYS102, DAT120, MAT100)

    Returns:
        Language code: 'en' for English, 'no' for Norwegian

    Rules:
        - FYS102, KJE101 → English (chemistry, engineering)
        - MAT100, DAT120 → Norwegian (math, computer science)
        - Default → English (safer for mixed content)
    """
    if not course_code:
        return "en"  # Default to English

    course_upper = course_code.upper()

    # English courses: FYS (physics), KJE (chemistry)
    if any(course_upper.startswith(prefix) for prefix in ["FYS", "KJE"]):
        return "en"

    # Norwegian courses: DAT (computer science), MAT (math)
    if any(course_upper.startswith(prefix) for prefix in ["DAT", "MAT"]):
        return "no"

    # Default to English for unknown courses
    return "en"


def extract_course_code_from_filename(filename: str) -> str:
    """
    Extract course code from filename.

    Args:
        filename: Filename like "FYS102_2025-10-03.mp3" or "DAT120-1 ..."

    Returns:
        Course code (e.g., "FYS102", "DAT120")
    """
    # Try pattern: EMNEKODE_YYYY-MM-DD
    match = re.match(r'^([A-Z]+\d+)_\d{4}-\d{2}-\d{2}', filename)
    if match:
        return match.group(1)

    # Try pattern: EMNEKODE-1 or just EMNEKODE at start
    match = re.match(r'^([A-Z]+\d+)', filename)
    if match:
        return match.group(1)

    return ""

def get_month_name(month_num: int) -> str:
    """Convert month number to Norwegian month name"""
    months = {
        1: "januar", 2: "februar", 3: "mars", 4: "april",
        5: "mai", 6: "juni", 7: "juli", 8: "august",
        9: "september", 10: "oktober", 11: "november", 12: "desember"
    }
    return months.get(month_num, "ukjent")

def parse_filename_details(file_path: str, verbose: bool = False) -> dict | None:
    """
    Parse a filename to extract course code, date, and other details.

    Expected format: EMNEKODE_YYYY-MM-DD.<ext>
    Example: FYS102_2025-10-03.txt

    Args:
        file_path: Path to the file
        verbose: If True, print detailed error messages on parse failure

    Returns:
        A dictionary with details or None if parsing fails.
    """
    basename = os.path.basename(file_path)

    # Regex to capture course code and date, ignoring extension
    match = re.match(r'^([A-Z]+\d+)_(\d{4})-(\d{2})-(\d{2})', basename)

    if not match:
        if verbose:
            print(f"\n❌ Filnavn-parsing feilet for: {basename}")
            print(f"   Forventet format: EMNEKODE_YYYY-MM-DD.ext")
            print(f"   Eksempel: FYS102_2025-10-03.txt")
            print(f"   Tips:")
            print(f"     - Emnekode må starte med store bokstaver + tall (f.eks. FYS102)")
            print(f"     - Dato må være på format YYYY-MM-DD")
            print(f"     - Separator mellom emnekode og dato må være underscore (_)")
        return None

    emnekode, year_str, month_str, day_str = match.groups()

    return {
        "course_code": emnekode,
        "year": int(year_str),
        "month": int(month_str),
        "day": int(day_str),
        "full_date": f"{year_str}-{month_str}-{day_str}",
        "month_name": get_month_name(int(month_str))
    }

def get_summary_filepath(transcription_filepath: str) -> str:
    """
    Construct the structured file path for a summary markdown file.

    Args:
        transcription_filepath: The path to the source transcription file.

    Returns:
        The target path for the summary .md file.
    """
    details = parse_filename_details(transcription_filepath)

    if not details:
        # Fallback to simple replacement if parsing fails
        return transcription_filepath.replace(".txt", ".md")

    folder_path = (
        f"forelesninger/{details['course_code']}/"
        f"{details['year']}_{details['month_name']}"
    )

    # Format: EMNEKODE_DD.MM.YY.md (e.g., KJE101_26.09.25.md)
    date_str = f"{details['day']:02d}.{details['month']:02d}.{details['year'] % 100:02d}"
    summary_filename = f"{details['course_code']}_{date_str}.md"

    return os.path.join(folder_path, summary_filename)

def check_file_on_github(file_path: str) -> bool:
    """
    Sjekk om en fil finnes på GitHub (remote repository).

    Args:
        file_path: Relativ path til filen (f.eks. "forelesninger/KJE101/2025_oktober/KJE101_03.10.25.md")

    Returns:
        True hvis filen finnes på remote, False ellers
    """
    def run_git(*args):
        """Helper to run git commands"""
        try:
            process = subprocess.run(
                ["git"] + list(args),
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=5
            )
            return process.returncode, process.stdout.strip(), process.stderr.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return 1, "", ""

    # Sjekk om vi er i et Git-repo
    rc, _, _ = run_git("rev-parse", "--is-inside-work-tree")
    if rc != 0:
        return False

    # Sjekk om vi har en remote
    rc, _, _ = run_git("remote", "get-url", "origin")
    if rc != 0:
        return False

    # Hent liste over filer på remote (origin/master eller origin/main)
    # Prøver først master, deretter main
    for branch in ["origin/master", "origin/main"]:
        rc, output, _ = run_git("ls-tree", "-r", "--name-only", branch)
        if rc == 0:
            remote_files = output.splitlines()
            return file_path in remote_files

    return False

def validate_git_setup(verbose: bool = True) -> dict:
    """
    Validate Git repository setup and configuration.

    Args:
        verbose: If True, print status messages

    Returns:
        Dictionary with validation results:
        {
            "is_git_repo": bool,
            "has_remote": bool,
            "remote_url": str or None,
            "is_clean": bool,
            "can_commit": bool,
            "errors": list of error messages
        }
    """
    result = {
        "is_git_repo": False,
        "has_remote": False,
        "remote_url": None,
        "is_clean": True,
        "can_commit": False,
        "errors": []
    }

    def run_git(*args):
        """Helper to run git commands"""
        try:
            process = subprocess.run(
                ["git"] + list(args),
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=5
            )
            return process.returncode, process.stdout.strip(), process.stderr.strip()
        except FileNotFoundError:
            return 127, "", "git ikke funnet"
        except subprocess.TimeoutExpired:
            return 1, "", "git-kommando timeout"

    if verbose:
        print("\n🔍 Validerer Git-oppsett...")

    # Check if git is installed
    rc, _, err = run_git("--version")
    if rc != 0:
        result["errors"].append("Git er ikke installert eller ikke i PATH")
        if verbose:
            print("❌ Git er ikke installert")
        return result

    # Check if this is a git repo
    rc, _, _ = run_git("rev-parse", "--is-inside-work-tree")
    if rc != 0:
        result["errors"].append("Ikke et Git-repository")
        if verbose:
            print("❌ Ikke et Git-repository")
            print("   Kjør: git init && git remote add origin <url>")
        return result

    result["is_git_repo"] = True

    # Check for remote
    rc, output, _ = run_git("remote", "get-url", "origin")
    if rc == 0 and output:
        result["has_remote"] = True
        result["remote_url"] = output
        if verbose:
            print(f"✓ Git remote: {output}")
    else:
        result["errors"].append("Ingen remote konfigurert")
        if verbose:
            print("⚠️  Ingen remote konfigurert")
            print("   Kjør: git remote add origin <url>")

    # Check if working tree is clean
    rc, output, _ = run_git("status", "--porcelain")
    if rc == 0:
        if output:
            result["is_clean"] = False
            if verbose:
                print(f"ℹ️  {len(output.splitlines())} ucommittede endringer")

    # Check if we can commit (user.name and user.email set)
    rc1, _, _ = run_git("config", "user.name")
    rc2, _, _ = run_git("config", "user.email")

    if rc1 == 0 and rc2 == 0:
        result["can_commit"] = True
        if verbose:
            print("✓ Git brukerinfo konfigurert")
    else:
        result["errors"].append("Git brukerinfo ikke konfigurert")
        if verbose:
            print("⚠️  Git brukerinfo ikke konfigurert")
            print("   Kjør: git config user.name 'Ditt Navn'")
            print("         git config user.email 'din@epost.no'")

    if verbose and result["is_git_repo"] and result["has_remote"] and result["can_commit"]:
        print("✓ Git-oppsett er klart for publisering\n")

    return result