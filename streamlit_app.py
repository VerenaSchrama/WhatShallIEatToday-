from dotenv import load_dotenv
load_dotenv()
import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
from utils import reset_session, load_llm_chain, add_to_chat_history
from auth_service import AuthService
from profile_service import ProfileService
from config import ERROR_MESSAGES, SUCCESS_MESSAGES, SESSION_TIMEOUT

# Load environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

auth_service = AuthService()
profile_service = ProfileService()

# Session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "personalization_completed" not in st.session_state:
    st.session_state.personalization_completed = False
if "login_attempts" not in st.session_state:
    st.session_state.login_attempts = 0
if "last_activity" not in st.session_state:
    st.session_state.last_activity = datetime.now()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Login/Register
if not st.session_state.logged_in:
    st.title("Cycle Nutrition Assistant (Simple)")
    auth_mode = st.radio("Login or Register", ["Login", "Register"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    # Add 'Forgot password?' button
    if st.button("Forgot password?"):
        st.session_state.show_reset = True

    # Show password reset form
    if st.session_state.get("show_reset"):
        reset_email = st.text_input("Enter your email to reset password")
        if st.button("Send reset link"):
            success, msg = auth_service.send_password_reset(reset_email)
            if success:
                st.success("Check your email for a reset link.")
            else:
                st.error(msg)
        st.stop()

    if auth_mode == "Register":
        confirm_password = st.text_input("Confirm Password", type="password")
        if st.button("Register"):
            if password != confirm_password:
                st.error("Passwords do not match")
            else:
                success, msg = auth_service.register_user(email, password)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    else:
        if st.button("Login"):
            success, user_data, msg = auth_service.login_user(email, password)
            if success:
                st.session_state.user_id = user_data["id"]
                st.session_state.logged_in = True
                st.session_state.login_attempts = 0
                st.experimental_rerun()
            else:
                st.session_state.login_attempts += 1
                st.error(msg)
    st.stop()

# Handle password reset via token in URL
query_params = st.experimental_get_query_params()
if "token" in query_params:
    token = query_params["token"][0]
    st.header("Reset Your Password")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm New Password", type="password")
    if st.button("Reset Password"):
        if new_password != confirm_password:
            st.error("Passwords do not match.")
        else:
            success, msg = auth_service.reset_password(token, new_password)
            if success:
                st.success("Password reset successful! You can now log in.")
            else:
                st.error(msg)
    st.stop()

# Personalization
st.header("Personalization")
phase = st.selectbox("Cycle phase", ["", "Menstrual", "Follicular", "Ovulatory", "Luteal"])
goal = st.selectbox("Support goal", ["Nothing specific", "Hormonal balance and regular cycle", "Getting back my period", "More energy", "Acne", "Eat more nutritious in general", "Digestive health/ Metabolism boost"])
diet = st.multiselect("Dietary preferences", ["Vegan", "Vegetarian", "Nut allergy", "Gluten free", "Lactose intolerance"])

if st.button("Save Personalization"):
    st.session_state.phase = phase
    st.session_state.support_goal = goal
    st.session_state.dietary_preferences = diet
    st.session_state.personalization_completed = True
    st.success("Personalization saved!")

if not st.session_state.get("personalization_completed"):
    st.info("Please complete personalization above.")
    st.stop()

# Chat
st.header("Ask a question")
user_question = st.text_input("Your question")
if st.button("Ask") and user_question:
    try:
        qa_chain = load_llm_chain()
        response = qa_chain.run({
            "phase": st.session_state.phase,
            "goal": st.session_state.support_goal,
            "diet": ", ".join(st.session_state.dietary_preferences),
            "question": user_question
        })
        add_to_chat_history("user", user_question)
        add_to_chat_history("assistant", response)
        st.success("Answer generated!")
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Show chat history
st.header("Chat History")
for role, msg in st.session_state.chat_history[-10:]:
    st.markdown(f"**{role.capitalize()}:** {msg}")
