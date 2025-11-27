import streamlit as st
import pandas as pd
from schedule import ScheduleOptimizer
from utils.normalize import normalize_type
from sb_functions import save_schedule, remove_course, save_courses

st.set_page_config(layout="wide")
st.title("Optimize Study Plan")

# stop if user hasn't uploaded any syllabi yet
if "courses" not in st.session_state or not st.session_state["courses"]:
    st.error("No courses found. Upload syllabi first.")
    st.stop()

# stop if user hasn't configured any study settings yet
if "settings" not in st.session_state:
    st.error("Settings not found. Configure them first.")
    st.stop()

courses = st.session_state["courses"]
settings = st.session_state["settings"]

daily_hours = settings.get("daily_hours", {})
work_ahead_days = settings.get("work_ahead_days", {})
base_hours = settings.get("base_hours", {})
semester_start = settings.get("semester_start")
semester_end = settings.get("semester_end")

# block user if semester dates were never saved on Upload/Settings page
if not semester_start or not semester_end:
    st.error("Semester dates not found. Go to Upload or Settings page and set them first.")
    st.stop()

# build editable assessment list only the first time the page loads
if "edited_assessments" not in st.session_state:
    all_assessments = []

    # convert parsed JSON structure into a flat table for user editing
    for course_json in courses.values():
        course_code = course_json.get("course_info", {}).get("course_code", "")
        breakdown = course_json.get("assessments", {}).get("breakdown", [])

        for a in breakdown:
            raw_type = a.get("type", "")
            atype = normalize_type(raw_type)

            entry = {
                "course_code": course_code,
                "type": atype,
                "title": a.get("title") or raw_type.title(),
                "due_date": a.get("due_date"),
                "hours_required": a.get("hours_required", base_hours.get(atype, 0))
            }
            all_assessments.append(entry)
    
    st.session_state["edited_assessments"] = all_assessments
else:
    # reuse cached edits so user changes persist across reruns
    all_assessments = st.session_state["edited_assessments"]

st.subheader("Filter by Course")

# dropdown lets user isolate a single course while editing
course_list = ["All Courses"] + list(courses.keys())
selected_course = st.selectbox("Select a course to view:", course_list)

if selected_course != "All Courses":
    filtered_assessments = [a for a in all_assessments if a["course_code"] == selected_course]
else:
    filtered_assessments = all_assessments

df = pd.DataFrame(filtered_assessments)

st.subheader("Edit Assessments")
st.write("You can edit hours, add new rows, or delete rows. Changes persist automatically.")

# main editor where user modifies assessment rows
edited_df = st.data_editor(
    df,
    hide_index=True,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "course_code": st.column_config.SelectboxColumn(
            "Course",
            options=list(courses.keys()),
            required=False
        ),
        "type": st.column_config.TextColumn("Type", required=False),
        "title": st.column_config.TextColumn("Title", required=False),
        "due_date": st.column_config.TextColumn(
            "Due Date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
            required=False
        ),
        "hours_required": st.column_config.NumberColumn(
            "Hours Required",
            min_value=0,
            max_value=500,
            step=1,
            format="%d",
            required=False
        )
    },
    key="assessment_editor"
)

# convert back to list of dicts for saving
updated_assessments = edited_df.to_dict(orient="records")

# when filtering by a single course, merge updates with untouched courses
if selected_course != "All Courses":
    other_assessments = [
        a for a in st.session_state["edited_assessments"]
        if a["course_code"] != selected_course
    ]
    updated_assessments = other_assessments + updated_assessments

# update session so edits persist across reruns
st.session_state["edited_assessments"] = updated_assessments

col1, col2 = st.columns(2)

with col1:
    # write user edits back to database
    if st.button("Save Changes to Database", use_container_width=True):

        # regroup assessments by course before saving
        course_assessments = {}
        
        for assessment in updated_assessments:
            course_code = assessment["course_code"]
            if course_code not in course_assessments:
                course_assessments[course_code] = []
            
            course_assessments[course_code].append({
                "type": assessment["type"],
                "title": assessment["title"],
                "due_date": assessment["due_date"],
                "hours_required": assessment["hours_required"]
            })
        
        # write updated breakdown back into session courses
        for course_code, assessments_list in course_assessments.items():
            if course_code in st.session_state["courses"]:
                if "assessments" not in st.session_state["courses"][course_code]:
                    st.session_state["courses"][course_code]["assessments"] = {}
                st.session_state["courses"][course_code]["assessments"]["breakdown"] = assessments_list
        
        # push changes to Supabase
        if "uid" in st.session_state:
            save_courses(st.session_state["uid"], st.session_state["courses"])
        
        st.success("Changes saved to database!")

with col2:
    # remove a single course entirely from the system
    if selected_course != "All Courses":
        if st.button(f"Remove {selected_course}", type="secondary", use_container_width=True):
            if "uid" in st.session_state:
                remove_course(st.session_state["uid"], selected_course)
            del st.session_state["courses"][selected_course]
            if "edited_assessments" in st.session_state:
                del st.session_state["edited_assessments"]
            st.success(f"{selected_course} removed!")
            st.rerun()

st.divider()

# generate study plan using edited data + settings
if st.button("Generate Study Plan", type="primary", use_container_width=True):

    optimizer = ScheduleOptimizer(
        semester_start=semester_start,
        semester_end=semester_end,
        daily_hours=daily_hours,
        work_ahead_days=work_ahead_days
    )

    # create raw schedule from weighted hours and due dates
    schedule = optimizer.generate_raw_schedule(updated_assessments)
    st.session_state["schedule"] = schedule

    # save full schedule to database
    if "uid" in st.session_state:
        save_schedule(st.session_state["uid"], schedule)

    st.success("Schedule generated! Redirecting...")
    st.switch_page("pages/3_Calendar.py")
