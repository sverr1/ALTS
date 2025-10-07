"""
ALTS Utility Functions
Shared helper functions for language detection and course code parsing
"""
import os
import re

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

def parse_filename_details(file_path: str) -> dict | None:
    """
    Parse a filename to extract course code, date, and other details.

    Expected format: EMNEKODE_YYYY-MM-DD.<ext>
    Example: FYS102_2025-10-03.txt

    Returns:
        A dictionary with details or None if parsing fails.
    """
    basename = os.path.basename(file_path)
    
    # Regex to capture course code and date, ignoring extension
    match = re.match(r'^([A-Z]+\d+)_(\d{4})-(\d{2})-(\d{2})', basename)
    
    if not match:
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