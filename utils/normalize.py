#helper to normalize assessment types for cleaner display

def normalize_type(t: str) -> str:
    t = (t or "").strip().lower()

    if "assignment" in t:
        return "assignment"
    if "quiz" in t:
        return "quiz"
    if "mid" in t and "term" in t:
        return "midterm"
    if "final" in t:
        return "final"
    if "exam" in t:
        return "exam"
    if "project" in t:
        return "project"
    if "present" in t:
        return "presentation"
    if "lab" in t:
        return "lab"
    if "report" in t:
        return "report"
    if "case" in t:
        return "case_study"
    if "discussion" in t:
        return "discussion"
    if "read" in t:
        return "reading"
    if "homework" in t or "hw" in t:
        return "homework"
    if "essay" in t:
        return "essay"

    return t 