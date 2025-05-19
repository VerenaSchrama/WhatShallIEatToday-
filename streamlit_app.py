from dotenv import load_dotenv
load_dotenv()
import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
from utils import reset_session, load_llm_chain, add_to_chat_history
from auth_service import AuthService
from profile_service import ProfileService
from config import (
    ERROR_MESSAGES, 
    SUCCESS_MESSAGES, 
    SESSION_TIMEOUT,
    SUPABASE_URL,
    SUPABASE_KEY,
    SUPPORT_OPTIONS,
    DIETARY_OPTIONS,
    CYCLE_PHASES
)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

auth_service = AuthService()
profile_service = ProfileService()

# Session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "guest_mode" not in st.session_state:
    st.session_state.guest_mode = False
if "personalization_completed" not in st.session_state:
    st.session_state.personalization_completed = False
if "login_attempts" not in st.session_state:
    st.session_state.login_attempts = 0
if "last_activity" not in st.session_state:
    st.session_state.last_activity = datetime.now()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Title
st.title("Cycle Nutrition Assistant")

# Login/Register or Guest Access
if not st.session_state.logged_in and not st.session_state.guest_mode:
    st.write("Welcome! Choose how you'd like to proceed:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Login or Register")
        auth_mode = st.radio("Select option", ["Login", "Register"])
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
            if st.button("Back to login/register"):
                st.session_state.show_reset = False
                st.rerun()
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
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    st.error(msg)
    
    with col2:
        st.subheader("Try as Guest")
        st.write("Experience the chatbot without creating an account")
        if st.button("Continue as Guest"):
            st.session_state.guest_mode = True
            st.rerun()
    
    st.stop()

# Handle password reset via token in URL
query_params = st.query_params
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

# Manual override first
st.markdown("#### Option 1: Choose your current cycle phase manually ⬇️")
phase_override = st.selectbox("", ["", "Menstrual", "Follicular", "Ovulatory", "Luteal"], index=0)

# Add divider/intro for auto detection
st.markdown("---")
st.markdown("#### Option 2: Or let me help you to find your current phase:")

has_cycle = st.radio("Do you have a (regular) menstrual cycle?", ("Yes", "No"))

if has_cycle == "Yes":
    today = datetime.now().date()
    st.session_state.second_last_period = st.date_input("Second most recent period start date", value=today)
    st.session_state.last_period = st.date_input("Most recent period start date", value=today)

    if st.session_state.last_period and st.session_state.second_last_period:
        if st.session_state.second_last_period > st.session_state.last_period:
            st.session_state.second_last_period, st.session_state.last_period = st.session_state.last_period, st.session_state.second_last_period

        if st.session_state.last_period != today and st.session_state.second_last_period != today:
            cycle_length = (st.session_state.last_period - st.session_state.second_last_period).days
            if cycle_length <= 10:
                st.error("Your periods seem too close together. Please check the entered dates.")
            else:
                st.session_state.cycle_length = cycle_length
                days_since_last = (today - st.session_state.last_period).days

                if days_since_last <= 5:
                    detected_phase = "Menstrual"
                elif days_since_last <= 14:
                    detected_phase = "Follicular"
                elif days_since_last <= 21:
                    detected_phase = "Ovulatory"
                else:
                    detected_phase = "Luteal"

                st.session_state.phase = phase_override if phase_override else detected_phase
                if not phase_override:
                    st.success(f"Based on your data, you are likely in the **{st.session_state.phase}** phase.")
                st.session_state.personalization_completed = True
else:
    st.subheader("No active menstrual cycle detected.")
    pseudo_choice = st.radio("Would you like:", ("Get general energetic advice", "Start with a pseudo-cycle based on a 28-day rhythm"))

    if pseudo_choice:
        if pseudo_choice == "🌿 Get general energetic advice":
            st.session_state.phase = "General"
        else:
            st.session_state.phase = "Menstrual"
            st.session_state.cycle_length = 28
        st.success(f"Selected: {pseudo_choice}")
        st.session_state.personalization_completed = True

# Manual override always takes precedence if selected
if phase_override and phase_override in ["Menstrual", "Follicular", "Ovulatory", "Luteal"]:
    st.session_state.phase = phase_override
    st.success(f"You selected: **{phase_override}** phase manually.")
    st.session_state.personalization_completed = True

# Support goal and dietary preferences
st.session_state.support_goal = st.selectbox("Support goal", [""] + SUPPORT_OPTIONS)
st.session_state.dietary_preferences = st.multiselect("Dietary preferences", DIETARY_OPTIONS)

if st.session_state.phase and st.session_state.support_goal and st.session_state.dietary_preferences:
    st.session_state.personalization_completed = True

if not st.session_state.get("personalization_completed"):
    st.info("Please complete personalization above.")
    st.stop()

# Add custom CSS for modern card UI with purple accent
st.markdown(
    """
    <style>
    body, .stApp {
        background-color: #FAFAFB !important;
        font-family: 'Inter', 'sans-serif';
    }
    .chat-container {
        background: #fff;
        border-radius: 18px;
        box-shadow: 0 2px 12px rgba(68, 35, 105, 0.08);
        padding: 2rem;
        margin-bottom: 100px;
        border: 1px solid #e3d6f3;
    }
    .fixed-input {
        position: fixed;
        bottom: 2rem;
        left: 0;
        width: 100vw;
        background: #FAFAFB;
        padding: 1rem 2rem 1rem 2rem;
        z-index: 100;
        border-top: 1px solid #e3d6f3;
    }
    .stButton>button {
        background: #442369;
        color: #fff;
        border-radius: 24px;
        border: none;
        padding: 0.5rem 2rem;
        font-size: 1.1rem;
        margin-top: 0.5rem;
        transition: background 0.2s;
    }
    .stButton>button:hover {
        background: #341a4d;
    }
    .stTextInput>div>div>input {
        border-radius: 24px;
        border: 1.5px solid #e3d6f3;
        padding: 0.75rem 1.5rem;
        font-size: 1.1rem;
        background: #fff;
    }
    .stMarkdown {
        font-size: 1.1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Show chat history in a scrollable container
st.markdown('<div class="chat-container">', unsafe_allow_html=True)
for role, msg in st.session_state.chat_history:
    st.markdown(f"**{role.capitalize()}:** {msg}")
st.markdown('</div>', unsafe_allow_html=True)

# Fixed input bar at the bottom
with st.container():
    st.markdown('<div class="fixed-input">', unsafe_allow_html=True)
    user_question = st.text_input("Your question", key="chat_input", label_visibility="collapsed")
    ask = st.button("Ask", key="ask_button")
    st.markdown('</div>', unsafe_allow_html=True)

if ask and user_question:
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
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Logout button for logged-in users
if st.session_state.logged_in:
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.personalization_completed = False
        st.session_state.chat_history = []
        st.rerun()

# Exit guest mode button
if st.session_state.guest_mode:
    if st.button("Exit Guest Mode"):
        st.session_state.guest_mode = False
        st.session_state.personalization_completed = False
        st.session_state.chat_history = []
        st.rerun()
