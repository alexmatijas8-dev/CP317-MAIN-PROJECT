from supabase_client import supabase

# Authenication

def sign_up(email, password):
    return supabase.auth.sign_up({"email": email, "password": password})

def sign_in(email, password):
    return supabase.auth.sign_in_with_password({"email": email, "password": password})

# Load User Data (Extract the _json field from each table's first row and return a dict)

def load_user_data(uid):
    out = {
        "courses": {},
        "settings": {},
        "schedule": {},
        "completions": {}
    }

    # Courses
    res = supabase.table("user_courses") \
        .select("courses_json") \
        .eq("user_id", uid) \
        .execute()
    if res.data:
        out["courses"] = res.data[0].get("courses_json") or {}

    # Settings
    res = supabase.table("user_settings") \
        .select("settings_json") \
        .eq("user_id", uid) \
        .execute()
    if res.data:
        out["settings"] = res.data[0].get("settings_json") or {}

    # Schedule
    res = supabase.table("user_schedule") \
        .select("schedule_json") \
        .eq("user_id", uid) \
        .execute()
    if res.data:
        out["schedule"] = res.data[0].get("schedule_json") or {}

    # Completions
    res = supabase.table("user_task_completion") \
        .select("completion_json") \
        .eq("user_id", uid) \
        .execute()
    if res.data:
        out["completions"] = res.data[0].get("completion_json") or {}

    return out

# Save Functions
def save_courses(uid, courses):
    supabase.table("user_courses").upsert(
        {
            "user_id": uid,
            "courses_json": courses,
        }
    ).execute()

def save_settings(uid, settings):
    supabase.table("user_settings").upsert(
        {
            "user_id": uid,
            "settings_json": settings,
        }
    ).execute()

def save_schedule(uid, schedule):
    supabase.table("user_schedule").upsert(
        {
            "user_id": uid,
            "schedule_json": schedule,
        }
    ).execute()

def save_completions(uid, completions):
    supabase.table("user_task_completion").upsert(
        {
            "user_id": uid,
            "completion_json": completions,
        }
    ).execute()

def remove_course(uid, course_code):
    res = supabase.table("user_courses") \
        .select("courses_json") \
        .eq("user_id", uid) \
        .execute()

    if not res.data:
        return {}
    courses = res.data[0].get("courses_json") or {}
    courses.pop(course_code, None)
    supabase.table("user_courses").upsert(
        {
            "user_id": uid,
            "courses_json": courses,
        }
    ).execute()

    return courses