import streamlit as st
from pathlib import Path
from scraper import SyllabusScraper
from sb_functions import save_courses
from sb_functions import save_settings

# set page layout and title
st.set_page_config(layout="wide")
st.title("Upload Syllabus PDFs")

# load API key from secrets if available
API_KEY = (
    st.secrets.get("OPENAI_API_KEY")
    if "OPENAI_API_KEY" in st.secrets
    else None
)

# make sure uploads folder exists for saving temp files
Path("uploads").mkdir(exist_ok=True)

st.subheader("Semester Settings")

col1, col2 = st.columns(2)
with col1:
    # restore saved value if user has settings in session
    semester_start = st.text_input(
        "Semester Start (YYYY-MM-DD)", 
        value=st.session_state.get("settings", {}).get("semester_start", "2025-09-04")
    )
with col2:
    # same idea but for semester end
    semester_end = st.text_input(
        "Semester End (YYYY-MM-DD)", 
        value=st.session_state.get("settings", {}).get("semester_end", "2025-12-06")
    )

if st.button("Save Semester Dates", use_container_width=True):
    # store dates in session so other pages can access them
    st.session_state["semester_start"] = semester_start
    st.session_state["semester_end"] = semester_end
    
    if "settings" not in st.session_state:
        st.session_state["settings"] = {}
    
    st.session_state["settings"]["semester_start"] = semester_start
    st.session_state["settings"]["semester_end"] = semester_end
    
    # push settings to database if logged in
    if "uid" in st.session_state:
        save_settings(st.session_state["uid"], st.session_state["settings"])
        st.success("Semester dates saved!")
    else:
        st.error("Please log in to save dates")

st.divider()

uploads = st.file_uploader(
    "Upload one or more syllabus PDFs",
    type=["pdf"],
    accept_multiple_files=True
)

if uploads and st.button("Parse All Syllabi", use_container_width=True):

    # create scraper instance to process PDFs
    scraper = SyllabusScraper(API_KEY)

    # load previous parsed courses so this doesn't overwrite them
    parsed_courses = st.session_state.get("courses", {}).copy()
    progress = st.progress(0)

    for i, up in enumerate(uploads, start=1):

        # save uploaded PDF to local temp folder
        tmp_path = Path("uploads") / up.name
        with tmp_path.open("wb") as f:
            f.write(up.getbuffer())

        # run the scraper on the PDF
        with st.spinner(f"Parsing {up.name}..."):
            data = scraper.scrape_syllabus(
                pdf_path=str(tmp_path),
                semester_start=semester_start,
                semester_end=semester_end
            )

        # use detected course code or fallback to filename
        course_code = data.get("course_info", {}).get("course_code", up.name)
        parsed_courses[course_code] = data

        # update progress bar
        progress.progress(i / len(uploads))

    # save parsed data into session
    st.session_state["courses"] = parsed_courses
    
    # also save to database if logged in
    if "uid" in st.session_state:
        save_courses(st.session_state["uid"], parsed_courses)

    st.success("All syllabi parsed and saved!")
