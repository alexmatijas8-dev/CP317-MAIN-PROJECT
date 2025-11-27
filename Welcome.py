import streamlit as st
from sb_functions import sign_in, sign_up, load_user_data

st.set_page_config(page_title="Study Planner", layout="wide")
st.title("Study Planner")

# Initialize session state
for key in ["user", "uid", "courses", "settings", "schedule", "completions"]:
    if key not in st.session_state:
        st.session_state[key] = None if key in ["user", "uid"] else {}

# Already logged in
if st.session_state["uid"]:
    st.success(f"Logged in")
    if st.button("Log out"):
        for key in ["user", "uid", "courses", "settings", "schedule", "completions"]:
            st.session_state[key] = None if key in ["user", "uid"] else {}
        st.rerun()
    st.info("Use the sidebar to navigate")
    st.stop()

# Login/Signup forms
tab1, tab2 = st.tabs(["Log in", "Sign up"])

with tab1:
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_pw")
    
    if st.button("Log in", type="primary"):
        if not email or not password:
            st.error("Please enter both email and password")
        else:
            try:
                res = sign_in(email, password)
                uid = res.user.id
                
                st.session_state["user"] = res.user
                st.session_state["uid"] = uid
                
                # Load user data
                data = load_user_data(uid)
                st.session_state["courses"] = data.get("courses", {})
                st.session_state["settings"] = data.get("settings", {})
                st.session_state["schedule"] = data.get("schedule", {})
                st.session_state["completions"] = data.get("completions", {})
                
                st.success("Logged in!")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

with tab2:
    email = st.text_input("Email", key="signup_email")
    pw1 = st.text_input("Password", type="password", key="signup_pw1")
    pw2 = st.text_input("Confirm Password", type="password", key="signup_pw2")
    
    if st.button("Sign up"):
        if not email or not pw1:
            st.error("Please enter email and password")
        elif pw1 != pw2:
            st.error("Passwords don't match")
        else:
            try:
                res = sign_up(email, pw1)
                uid = res.user.id
                
                st.session_state["user"] = res.user
                st.session_state["uid"] = uid
                st.session_state["courses"] = {}
                st.session_state["settings"] = {}
                st.session_state["schedule"] = {}
                st.session_state["completions"] = {}
                
                st.success("Account created!")
                st.rerun()
            except Exception as e:
                st.error(f"Signup failed: {e}")