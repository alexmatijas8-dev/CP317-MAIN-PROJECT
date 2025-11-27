from datetime import datetime, date, time, timedelta
from typing import Dict, Any, List


def schedule_to_ics(schedule: Dict[str, Any],
                    courses: Dict[str, Any] = None,
                    calendar_name: str = "Study Schedule") -> str:

    days: List[Dict[str, Any]] = schedule.get("days", [])

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SyllabusPlanner//EN",
        f"X-WR-CALNAME:{calendar_name}",
    ]

    now_utc = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    # Process study session events
    for day in days:
        day_date = datetime.strptime(day["date"], "%Y-%m-%d").date()
        current_start = datetime.combine(day_date, time(9, 0))

        for t in day.get("tasks", []):
            hours = float(t.get("hours", 1.0))
            minutes = int(hours * 60)

            dt_start = current_start
            dt_end = dt_start + timedelta(minutes=minutes)

            course_code = t.get("course_code", "")
            title = t.get("title") or t.get("type", "Study Block")
            summary = f"{course_code} – {title}".strip(" –")

            description_parts = [
                f"Type: {t.get('type', '')}",
                f"Due date: {t.get('due_date', '')}",
                f"Planned hours: {hours}",
            ]
            description = "\\n".join(description_parts)

            uid = (
                f"{day['date']}-{course_code}-"
                f"{t.get('assessment_id', 0)}-{minutes}@syllabusplanner"
            )

            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now_utc}",
                f"DTSTART:{dt_start.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{dt_end.strftime('%Y%m%dT%H%M%S')}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{description}",
                "END:VEVENT",
            ])

            current_start = dt_end

    # Process due date events
    if courses:
        for course_code, course_data in courses.items():
            assessments = course_data.get("assessments", {}).get("breakdown", [])
            
            for assessment in assessments:
                due_date_str = assessment.get("due_date")
                if not due_date_str:
                    continue
                
                # Parse due date (with or without time)
                if "T" in due_date_str:
                    # Has time: "2025-11-25T23:59:00"
                    due_dt = datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M:%S")
                else:
                    # Date only: "2025-11-25" - default to 11:59 PM
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                    due_dt = datetime.combine(due_date.date(), time(23, 59, 0))
                
                # Create due date event (1 minute duration)
                dt_start = due_dt
                dt_end = due_dt + timedelta(minutes=1)
                
                assessment_type = assessment.get("type", "Assessment")
                summary = f"DUE: {course_code} – {assessment_type}"
                
                description_parts = [
                    f"Course: {course_data.get('course_info', {}).get('course_name', '')}",
                    f"Type: {assessment_type}",
                    f"Weight: {assessment.get('weight', 0)}%",
                ]
                
                notes = assessment.get("notes")
                if notes:
                    description_parts.append(f"Notes: {notes}")
                
                description = "\\n".join(description_parts)
                
                uid = f"due-{course_code}-{assessment_type}-{due_date_str}@syllabusplanner"
                
                lines.extend([
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTAMP:{now_utc}",
                    f"DTSTART:{dt_start.strftime('%Y%m%dT%H%M%S')}",
                    f"DTEND:{dt_end.strftime('%Y%m%dT%H%M%S')}",
                    f"SUMMARY:{summary}",
                    f"DESCRIPTION:{description}",
                    "END:VEVENT",
                ])

    lines.append("END:VCALENDAR")

    return "\r\n".join(lines)