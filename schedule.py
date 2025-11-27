from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Dict, Any


DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


@dataclass
class DaySlot:

    date: date
    weekday: str
    capacity: float
    tasks: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def remaining(self) -> float:
        used = sum(t["hours"] for t in self.tasks)
        return max(self.capacity - used, 0.0)


class ScheduleOptimizer:

    def __init__(
        self,
        semester_start: str,
        semester_end: str,
        daily_hours: Dict[str, float],
        work_ahead_days: Dict[str, int],
    ):
        self.semester_start = datetime.strptime(semester_start, "%Y-%m-%d").date()
        self.semester_end = datetime.strptime(semester_end, "%Y-%m-%d").date()
        self.daily_hours = {k.lower(): float(v) for k, v in daily_hours.items()}
        self.work_ahead_days = {k.lower(): int(v) for k, v in work_ahead_days.items()}

        self.days = self._build_day_slots()

    # Calendar construction

    def _build_day_slots(self) -> List[DaySlot]:
        days: List[DaySlot] = []
        current = self.semester_start
        while current <= self.semester_end:
            weekday_index = current.weekday()  # Monday=0
            weekday_name = DAY_NAMES[weekday_index]
            capacity = self.daily_hours.get(weekday_name, 0.0)
            days.append(DaySlot(date=current, weekday=weekday_name, capacity=capacity))
            current += timedelta(days=1)
        return days

    def _find_days_in_window(self, start: date, end: date) -> List[DaySlot]:
        return [d for d in self.days if start <= d.date <= end and d.capacity > 0.0]

    def _round_to_half_hour(self, hours: float) -> float:
        return round(hours * 2) / 2

    # Scheduling core
 
    def _compute_work_window(self, due_date_str: str, atype: str) -> tuple[date, date]:
        
        # Handle both date formats (with and without time)
        if "T" in due_date_str:
            due = datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M:%S").date()
        else:
            due = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        
        atype_lower = atype.lower()
        days_before = self.work_ahead_days.get(atype_lower, 7)
        start = due - timedelta(days=days_before)
        if start < self.semester_start:
            start = self.semester_start
        if due > self.semester_end:
            due = self.semester_end
        return start, due

    def _allocate_assessment(
        self,
        assessment: Dict[str, Any],
        assessment_id: int,
    ) -> Dict[str, Any]:
        atype = (assessment.get("type") or "unknown").lower()
        due_date = assessment.get("due_date")
        hours_required = float(assessment.get("hours_required", 0.0))

        if not due_date or hours_required <= 0:
            return {
                "assessment_id": assessment_id,
                "scheduled_hours": 0.0,
                "unscheduled_hours": hours_required,
                "status": "skipped_missing_date_or_zero_hours",
            }

        start, end = self._compute_work_window(due_date, atype)
        window_days = self._find_days_in_window(start, end)

        if not window_days:

            # No available days in window

            return {
                "assessment_id": assessment_id,
                "scheduled_hours": 0.0,
                "unscheduled_hours": hours_required,
                "status": "no_available_days",
            }

        remaining = hours_required

        # Fill days sequentially
        for d in window_days:
            if remaining <= 0.25:
                break
            
            # Check how much can be allocated to specific day
            available = d.remaining
            if available < 0.25:
                continue
            
            # Allocate as much as possible to this day (up to remaining)
            alloc = min(available, remaining)
            
            # Round to 0.5 hour increments
            alloc_rounded = self._round_to_half_hour(alloc)
            
            # If rounding up would exceed capacity or remaining, round down
            if alloc_rounded > available or alloc_rounded > remaining:
                alloc_rounded = self._round_to_half_hour(alloc - 0.25)
            
            # Skip if rounded value is invalid
            if alloc_rounded <= 0 or alloc_rounded > available:
                continue
            
            # Record this allocation
            d.tasks.append({
                "assessment_id": assessment_id,
                "course_code": assessment.get("course_code"),
                "type": assessment.get("type"),
                "title": assessment.get("title") or assessment.get("type"),
                "due_date": due_date,
                "hours": alloc_rounded,
            })
            remaining -= alloc_rounded

        scheduled = hours_required - remaining
        return {
            "assessment_id": assessment_id,
            "scheduled_hours": self._round_to_half_hour(scheduled),
            "unscheduled_hours": self._round_to_half_hour(max(remaining, 0.0)),
            "status": "ok" if remaining <= 1e-3 else "incomplete_capacity",
        }

    def generate_raw_schedule(self, assessments: List[Dict[str, Any]]) -> Dict[str, Any]:
        allocation_summaries = []

        for idx, a in enumerate(assessments):
            summary = self._allocate_assessment(a, assessment_id=idx)
            allocation_summaries.append(summary)

        # Build per-day schedule structure
        day_entries = []
        for d in self.days:
            if not d.tasks:
                continue
            day_entries.append({
                "date": d.date.strftime("%Y-%m-%d"),
                "weekday": d.weekday,
                "available_hours": d.capacity,
                "scheduled_hours": self._round_to_half_hour(sum(t["hours"] for t in d.tasks)),
                "tasks": d.tasks,
            })

        return {
            "days": day_entries,
            "allocations": allocation_summaries,
        }