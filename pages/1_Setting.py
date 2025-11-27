import streamlit as st
from utils.normalize import normalize_type
from sb_functions import save_settings

st.title("Study Settings & Preferences")

# stop here if user hasn't uploaded/parsed syllabi yet
if "courses" not in st.session_state or not st.session_state["courses"]:
    st.warning("No parsed syllabi found. Go to Upload page first.")
    st.stop()

courses = st.session_state["courses"]

# collect all unique assessment types found across uploaded syllabi
found_types = set()
for course_data in courses.values():
    assessments = course_data.get("assessments", {}).get("breakdown", [])
    for a in assessments:
        raw = a.get("type", "")
        found_types.add(normalize_type(raw))

found_types = sorted(found_types)

st.subheader("Semester Dates")

# pull semester dates from saved settings
stored_settings = st.session_state.get("settings", {})
semester_start = stored_settings.get("semester_start", "Not set")
semester_end = stored_settings.get("semester_end", "Not set")

st.info(f"**Semester Start:** {semester_start}  \n**Semester End:** {semester_end}")
st.caption("To change semester dates, go to the Upload page")

st.divider()

st.subheader("Daily Study Hours")

# default zero-hours for days with no saved settings
default_daily = {
    "monday": 0, "tuesday": 0, "wednesday": 0,
    "thursday": 0, "friday": 0, "saturday": 0, "sunday": 0
}

# load saved daily hours if they exist
stored_daily = st.session_state.get("settings", {}).get("daily_hours", default_daily)

days = list(default_daily.keys())
display_daily = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# UI numeric fields for each day's hours
daily_hours = {}
cols = st.columns(7)
for i, day in enumerate(days):
    with cols[i]:
        daily_hours[day] = st.number_input(
            display_daily[i],
            0.0, 24.0,
            float(stored_daily.get(day, 0)),
            step=0.5
        )

st.divider()

with st.expander("Work-Ahead Defaults (Days Before Due Date)", expanded=False):

    # fallback defaults if user hasn't changed anything yet
    default_work_days = {
        "assignment": 7, "quiz": 3, "lab": 1,
        "midterm": 10, "exam": 20, "final": 20,
        "project": 20, "presentation": 7,
        "essay": 20, "report": 10,
        "case_study": 3, "discussion": 1,
        "reading": 1, "homework": 1,
        "participation": 0
    }

    # load previously saved values if available
    stored_work = st.session_state.get("settings", {}).get("work_ahead_days", {})

    work_ahead_days = {}

    # create input fields for each assessment type actually found
    for t in found_types:
        display_name = t.capitalize().replace("_", " ")
        work_ahead_days[t] = st.number_input(
            f"{display_name} (days before due date)",
            0, 90,
            int(stored_work.get(t, default_work_days.get(t, 0)))
        )

st.divider()

with st.expander("Default Base Hours per Assessment Type", expanded=False):

    # fallback base-hour defaults
    default_base_hours = {
        "assignment": 4, "quiz": 3, "lab": 3,
        "midterm": 12, "exam": 20, "final": 20,
        "project": 25, "presentation": 10,
        "essay": 20, "report": 10,
        "case_study": 8, "discussion": 2,
        "reading": 2, "homework": 2,
        "participation": 1
    }

    # load saved values if they exist
    stored_base = st.session_state.get("settings", {}).get("base_hours", {})

    base_hours = {}

    # input fields for each assessment type found in uploaded syllabi
    for t in found_types:
        display_name = t.capitalize().replace("_", " ")
        base_hours[t] = st.number_input(
            f"{display_name} Hours",
            1, 200,
            int(stored_base.get(t, default_base_hours.get(t, 3)))
        )

# save everything the user edited on this page
if st.button("Save Settings"):
    st.session_state["settings"] = {
        "semester_start": semester_start,
        "semester_end": semester_end,
        "daily_hours": daily_hours,
        "work_ahead_days": work_ahead_days,
        "base_hours": base_hours
    }

    # push settings to database for logged-in users
    if "uid" in st.session_state:
        save_settings(st.session_state["uid"], st.session_state["settings"])

    # clear cached edited assessments so recalculation uses new defaults
    if "edited_assessments" in st.session_state:
        del st.session_state["edited_assessments"]

    st.success("Settings saved! Assessments will refresh with new defaults.")
