import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
from dotenv import load_dotenv

from ui import (
    render_personalization_sidebar,
    render_cycle_questions,
    render_personalization_summary,
)
from utils import reset_session, load_llm_chain, add_to_chat_history
from auth_service import AuthService
from profile_service import ProfileService
from profile_ui import render_profile_page
from config import (
    ERROR_MESSAGES,
    SUCCESS_MESSAGES,
    SESSION_TIMEOUT
)

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize services
auth_service = AuthService()
profile_service = ProfileService()

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "personalization_completed" not in st.session_state:
    st.session_state.personalization_completed = False
if "login_attempts" not in st.session_state:
    st.session_state.login_attempts = 0
if "last_activity" not in st.session_state:
    st.session_state.last_activity = datetime.now()
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"

def check_session_timeout():
    if st.session_state.logged_in:
        time_diff = (datetime.now() - st.session_state.last_activity).total_seconds()
        if time_diff > SESSION_TIMEOUT:
            st.session_state.logged_in = False
            st.error(ERROR_MESSAGES["session_expired"])
            st.rerun()

def update_last_activity():
    st.session_state.last_activity = datetime.now()

# Check session timeout
check_session_timeout()

if not st.session_state.logged_in:
    st.title("Your Cycle Nutrition Assistant")
    st.markdown("_Ask your hormonal, PCOS & food questions to science._")

    auth_mode = st.radio("Do you want to log in or register (for first timer's)?", ["Login", "Register"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if auth_mode == "Register":
        confirm_password = st.text_input("Confirm Password", type="password")
        if st.button("Register"):
            if password != confirm_password:
                st.error(ERROR_MESSAGES["password_mismatch"])
            else:
                success, msg = auth_service.register_user(email, password)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    elif auth_mode == "Login":
        if st.button("Login"):
            if st.session_state.login_attempts >= 3:
                st.error("Too many login attempts. Please try again later.")
            else:
                success, user_data, msg = auth_service.login_user(email, password)
                if success:
                    st.session_state.user_id = user_data["id"]
                    st.session_state.session_token = user_data["session_token"]
                    st.session_state.logged_in = True
                    st.session_state.login_attempts = 0
                    update_last_activity()
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    st.error(msg)

    # Add password reset option
    if st.button("Forgot Password?"):
        if email:
            success, msg = auth_service.reset_password(email)
            if success:
                st.success(msg)
            else:
                st.error(msg)
        else:
            st.error("Please enter your email address first")

    st.stop()

# Verify session token
if st.session_state.logged_in:
    success, user_id = auth_service.verify_session(st.session_state.session_token)
    if not success:
        st.session_state.logged_in = False
        st.error(user_id)  # user_id contains error message in this case
        st.rerun()

# Update last activity
update_last_activity()

# Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Profile"])
st.session_state.current_page = page.lower()

if st.session_state.current_page == "profile":
    render_profile_page(profile_service, st.session_state.user_id)
else:
    # --- Load or initialize profile ---
    try:
        user_data = supabase.table("profiles").select("*").eq("user_id", st.session_state.user_id).execute()

        if not user_data.data:
            supabase.table("profiles").insert({
                "user_id": st.session_state.user_id,
                "phase": "",
                "goal": "",
                "diet": []
            }).execute()
            st.info("New profile created. Please personalize your settings.")
        else:
            profile = user_data.data[0]
            st.session_state.phase = profile.get("phase", "")
            st.session_state.support_goal = profile.get("goal", "")
            st.session_state.dietary_preferences = profile.get("diet", [])
    except Exception as e:
        st.error(f"Error loading profile: {str(e)}")
        st.stop()

    # --- App Content ---
    st.title("Your Cycle Nutrition Assistant")
    st.write("*Ask your hormonal, PCOS & food questions to science.*")

    # --- Personalization ---
    has_cycle = render_cycle_questions()
    render_personalization_sidebar()

    if st.sidebar.button("💾 Save Settings"):
        try:
            supabase.table("profiles").update({
                "phase": st.session_state.phase,
                "goal": st.session_state.support_goal,
                "diet": st.session_state.dietary_preferences
            }).eq("user_id", st.session_state.user_id).execute()
            st.session_state.personalization_completed = True
            st.sidebar.success(SUCCESS_MESSAGES["settings_saved"])
        except Exception as e:
            st.sidebar.error(f"Error saving settings: {str(e)}")

    # --- Chat interface ---
    if st.session_state.personalization_completed:
        render_personalization_summary()

        user_question = st.chat_input("Ask something like: 'What should I eat in my luteal phase?'")
        if user_question:
            try:
                qa_chain = load_llm_chain()
                response = qa_chain.run({
                    "phase": st.session_state.phase,
                    "goal": st.session_state.support_goal,
                    "diet": ", ".join(st.session_state.dietary_preferences),
                    "question": user_question
                })

                supabase.table("chat_history").insert({
                    "user_id": st.session_state.user_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "question": user_question,
                    "response": response
                }).execute()

                add_to_chat_history("user", user_question)
                add_to_chat_history("assistant", response)
            except Exception as e:
                st.error(f"Error processing your question: {str(e)}")

        st.markdown("---")
        st.subheader("🕓 Chat History")

        try:
            history = supabase.table("chat_history").select("*").eq("user_id", st.session_state.user_id).order("timestamp", desc=True).limit(5).execute()
            for msg in reversed(history.data):
                st.chat_message("user").markdown(msg["question"])
                st.chat_message("assistant").markdown(msg["response"])
        except Exception as e:
            st.error(f"Error loading chat history: {str(e)}")
    else:
        st.info("✨ Please complete the personalization steps above before asking questions.")
