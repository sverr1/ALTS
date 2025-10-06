"""
ALTS Utility Functions
Shared helper functions for language detection and course code parsing
"""

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
    import re

    # Try pattern: EMNEKODE_YYYY-MM-DD
    match = re.match(r'^([A-Z]+\d+)_\d{4}-\d{2}-\d{2}', filename)
    if match:
        return match.group(1)

    # Try pattern: EMNEKODE-1 or just EMNEKODE at start
    match = re.match(r'^([A-Z]+\d+)', filename)
    if match:
        return match.group(1)

    return ""
