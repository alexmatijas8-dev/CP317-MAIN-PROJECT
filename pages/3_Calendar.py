import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from sb_functions import save_completions
from utils.ics_exporter import schedule_to_ics

# helper to format hours into readable text

def format_hours(hours: float) -> str:
    if hours == 0:
        return "0 min"
    whole_hours = int(hours)
    minutes = int((hours - whole_hours) * 60)
    parts = []
    if whole_hours == 1:
        parts.append("1 hour")
    elif whole_hours > 1:
        parts.append(f"{whole_hours} hours")
    if minutes == 30:
        parts.append("30 min")
    elif minutes > 0:
        parts.append(f"{minutes} min")
    return " and ".join(parts) if parts else "0 min"


# page setup
st.set_page_config(page_title="Weekly Calendar", layout="wide")
st.title("Weekly Study Calendar")

# stop if schedule is missing
if "schedule" not in st.session_state:
    st.error("No schedule found. Generate a schedule on the Optimize page first.")
    st.stop()

schedule = st.session_state["schedule"]
days = schedule.get("days", [])

# stop if schedule somehow loaded but is empty
if not days:
    st.error("Schedule is empty. Please re-run optimization.")
    st.stop()

df = pd.DataFrame(days)
df["date"] = pd.to_datetime(df["date"])

# store checked-off tasks for each day
if "completions" not in st.session_state:
    st.session_state["completions"] = {}

# custom UI CSS for day cards
st.markdown(
    """
<style>
...
</style>
""",
    unsafe_allow_html=True
)

# week index controls which week of the schedule is displayed
if "calendar_week_index" not in st.session_state:
    st.session_state["calendar_week_index"] = 0

start_date = df["date"].min()
end_date = df["date"].max()

# build a list of week start dates across the entire semester
all_weeks = []
cursor = start_date
while cursor <= end_date:
    all_weeks.append(cursor)
    cursor += timedelta(days=7)

week_index = max(0, min(st.session_state["calendar_week_index"], len(all_weeks) - 1))
st.session_state["calendar_week_index"] = week_index

current_week_start = all_weeks[week_index]
current_week_end = current_week_start + timedelta(days=6)

st.header(f"Week of {current_week_start.strftime('%B %d, %Y')}")

# navigation buttons for switching between weeks
col1, col2, col3, col4 = st.columns([1, 1, 1, 6])

with col1:
    if st.button("Previous Week") and week_index > 0:
        st.session_state["calendar_week_index"] -= 1
        st.rerun()

with col2:
    # find which week today's date belongs to
    if st.button("Jump to Today"):
        today = pd.Timestamp(datetime.now().date())
        for i, week_start in enumerate(all_weeks):
            week_end = week_start + timedelta(days=6)
            if week_start <= today <= week_end:
                st.session_state["calendar_week_index"] = i
                st.rerun()
                break

with col3:
    if st.button("Next Week") and week_index < len(all_weeks) - 1:
        st.session_state["calendar_week_index"] += 1
        st.rerun()

with col4:
    pass  # empty column used for spacing

# slice out just the selected week
week_df = df[(df["date"] >= current_week_start) & (df["date"] <= current_week_end)]

st.subheader("Weekly Overview")

week_dates = list(pd.date_range(current_week_start, current_week_end))

courses = st.session_state.get("courses", {})

# build a mapping of due dates to assessments (for markers on day cards)
due_dates_map = {}
for course_code, course_data in courses.items():
    assessments = course_data.get("assessments", {}).get("breakdown", [])
    for assessment in assessments:
        due_date_str = assessment.get("due_date")
        if not due_date_str:
            continue
        
        # parse date or datetime
        if "T" in due_date_str:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M:%S").date()
        else:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        
        if due_date not in due_dates_map:
            due_dates_map[due_date] = []
        
        due_dates_map[due_date].append({
            "course_code": course_code,
            "type": assessment.get("type", "Assessment"),
            "title": assessment.get("title", assessment.get("type", "Assessment")),
            "due_date_str": due_date_str
        })

# build HTML for weekly cards
cards_html = '<div class="card-container">'

for day_date in week_dates:
    day_rows = week_df[week_df["date"] == day_date]
    
    is_today = day_date.date() == datetime.now().date()
    today_class = "today" if is_today else ""

    cards_html += f"""
    <div class="day-card {today_class}">
        <div class="day-title">{day_date.strftime('%A')}</div>
        <div class="date-text">{day_date.strftime('%b %d')}</div>
    """

    has_tasks = False

    # add study tasks for the day
    if not day_rows.empty:
        for _, row in day_rows.iterrows():
            for task in row["tasks"]:
                has_tasks = True
                formatted_time = format_hours(task["hours"])
                due_date = task.get("due_date", "")

                # tooltip for due dates
                if due_date:
                    try:
                        if "T" in due_date:
                            due = datetime.strptime(due_date, "%Y-%m-%dT%H:%M:%S")
                            days_until = (due.date() - day_date.date()).days
                            tooltip_text = f"Due: {due.strftime('%B %d, %Y at %I:%M %p')} ({days_until} days)"
                        else:
                            due = datetime.strptime(due_date, "%Y-%m-%d")
                            days_until = (due.date() - day_date.date()).days
                            tooltip_text = f"Due: {due.strftime('%B %d, %Y')} ({days_until} days)"
                    except:
                        tooltip_text = f"Due: {due_date}"
                else:
                    tooltip_text = "No due date"
                
                # task line HTML
                cards_html += (
                    f"<div class='task-text'>"
                    f"• <b>{task['course_code']}</b><br>"
                    f"{task['title']} ({formatted_time})"
                    f"<span class='tooltip'>{tooltip_text}</span>"
                    f"</div>"
                )
    
    # add due markers for tasks actually due on that calendar date
    day_date_only = day_date.date()
    if day_date_only in due_dates_map:
        for due_item in due_dates_map[day_date_only]:
            has_tasks = True
            course_code = due_item["course_code"]
            assessment_title = due_item.get("title", due_item["type"])
            due_date_str = due_item["due_date_str"]
            
            if "T" in due_date_str:
                due_dt = datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M:%S")
                tooltip_text = f"Due at {due_dt.strftime('%I:%M %p')}"
            else:
                tooltip_text = "Due today"
            
            cards_html += (
                f"<div class='due-marker'>"
                f"📌 <b>{course_code}</b><br>"
                f"{assessment_title} DUE"
                f"<span class='tooltip'>{tooltip_text}</span>"
                f"</div>"
            )

    if not has_tasks:
        cards_html += "<div class='task-text'>No tasks.</div>"

    cards_html += "</div>"

cards_html += "</div>"

# render the weekly calendar cards
st.markdown(cards_html, unsafe_allow_html=True)

st.divider()
st.subheader("Today's Tasks")

# pull today's tasks from schedule
today = datetime.now().date()
today_str = today.strftime("%Y-%m-%d")
today_schedule = [day for day in days if day["date"] == today_str]

if today_schedule and today_schedule[0].get("tasks"):
    completed_today = st.session_state["completions"].get(today_str, [])
    
    # interactive checkboxes for each task
    for task in today_schedule[0]["tasks"]:
        task_id = f"{task['course_code']}-{task['title']}"
        
        is_completed = task_id in completed_today
        
        completed = st.checkbox(
            f"**{task['course_code']}** - {task['title']} ({format_hours(task['hours'])})",
            value=is_completed,
            key=f"task_{task_id}"
        )
        
        # handle task completion toggles
        if completed and not is_completed:
            if today_str not in st.session_state["completions"]:
                st.session_state["completions"][today_str] = []
            st.session_state["completions"][today_str].append(task_id)
            
            if "uid" in st.session_state:
                save_completions(st.session_state["uid"], st.session_state["completions"])
            
            st.success("Task completed!")
            st.rerun()
            
        elif not completed and is_completed:
            st.session_state["completions"][today_str].remove(task_id)
            
            if "uid" in st.session_state:
                save_completions(st.session_state["uid"], st.session_state["completions"])
            
            st.rerun()
else:
    st.info("No tasks scheduled for today!")

st.divider()
st.subheader("Export Calendar")

# convert schedule into downloadable ICS file
courses = st.session_state.get("courses", {})
ics_text = schedule_to_ics(schedule, courses)

st.download_button(
    label="Download as .ics file",
    data=ics_text,
    file_name="study_schedule.ics",
    mime="text/calendar",
)
