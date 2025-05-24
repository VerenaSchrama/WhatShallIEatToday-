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
import streamlit.components.v1 as components
import json
from fpdf import FPDF
import time

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

# Initialize session state variables for personalization and chat
if "phase" not in st.session_state:
    st.session_state.phase = None
if "support_goal" not in st.session_state:
    st.session_state.support_goal = ""
if "dietary_preferences" not in st.session_state:
    st.session_state.dietary_preferences = []

# Logo at the top
st.image("images/HerFoodCodeLOGO.png", width=120)

# Title
st.title("Your Scientific Cycle Nutrition Assistant")

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

# Support goal and dietary preferences FIRST
st.session_state.support_goal = st.selectbox("Support goal", ["Select..."] + SUPPORT_OPTIONS)
st.session_state.dietary_preferences = st.multiselect("Dietary preferences", DIETARY_OPTIONS)

# Add divider before Option 1
st.markdown("---")

# Manual override first
st.markdown("#### Option 1: Choose your current cycle phase manually ⬇️")
phase_override = st.selectbox(
    "Select your current cycle phase (optional)",
    ["Select..."] + ["Menstrual", "Follicular", "Ovulatory", "Luteal"],
    index=0,
    label_visibility="collapsed"
)

# Add intro for auto detection (no divider here)
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

if st.session_state.phase and st.session_state.support_goal and st.session_state.dietary_preferences:
    st.session_state.personalization_completed = True

if not st.session_state.get("personalization_completed"):
    st.info("Please complete personalization above.")
    st.stop()

# --- Chat area: chat bubbles with speaker labels ---
st.markdown('''
<style>
.chat-bubble-user {
    background: #2d2d2d;
    color: #fff;
    border-radius: 16px 16px 4px 16px;
    padding: 1rem;
    margin-bottom: 0.5rem;
    margin-left: 20%;
    margin-right: 0;
    text-align: right;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.chat-bubble-assistant {
    background: #232323;
    color: #fff;
    border-radius: 16px 16px 16px 4px;
    padding: 1rem;
    margin-bottom: 1.5rem;
    margin-right: 20%;
    margin-left: 0;
    text-align: left;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.speaker-label {
    font-weight: bold;
    font-size: 0.95em;
    margin-bottom: 0.2em;
    color: #e07a5f;
}
</style>
''', unsafe_allow_html=True)

if st.session_state.get("personalization_completed"):
    st.header("Chat History")
    if st.session_state.chat_history:
        for role, msg in st.session_state.chat_history:
            if role == "user":
                st.markdown(f'''<div class="chat-bubble-user"><div class="speaker-label">You</div>{msg}</div>''', unsafe_allow_html=True)
            else:
                st.markdown(f'''<div class="chat-bubble-assistant"><div class="speaker-label">Assistant</div>{msg}</div>''', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#888; margin:2em 0; text-align:center;">Start the conversation by asking your first question below!</div>', unsafe_allow_html=True)

# Input at the bottom, always visible after latest message
if st.session_state.get("clear_chat_input"):
    st.session_state["chat_input"] = ""
    st.session_state["clear_chat_input"] = False

# --- Use Streamlit's st.chat_input for always-visible chat input ---
user_question = st.chat_input("Type your question...")
if user_question:
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
        st.rerun()
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

# --- Always-Visible Personalization Summary in Sidebar ---
st.sidebar.markdown("## Your Personalization Summary")
if st.session_state.get("phase"):
    st.sidebar.markdown(f"**Cycle phase:** {st.session_state.phase}")
else:
    st.sidebar.markdown("**Cycle phase:** _Not set_")
if st.session_state.get("support_goal"):
    st.sidebar.markdown(f"**Support goal:** {st.session_state.support_goal}")
else:
    st.sidebar.markdown("**Support goal:** _Not set_")
if st.session_state.get("dietary_preferences"):
    st.sidebar.markdown(f"**Dietary preferences:** {', '.join(st.session_state.dietary_preferences)}")
else:
    st.sidebar.markdown("**Dietary preferences:** _None_")
st.sidebar.markdown("---")

# --- Suggested Questions Panel in Sidebar ---
suggested_questions = [
    "Give me a personal overview of the 4 cycle phases and an extensive list of foods you recommend.",
    "What foods are best for my current cycle phase?",
    "Give me a 3-day breakfast plan.",
    "Why is organic food important for my cycle?",
    "What nutritional seeds support my phase (seed syncing)?"
]

st.sidebar.markdown("## 💡 Suggested Questions")
for i, question in enumerate(suggested_questions):
    if st.sidebar.button(question, key=f"suggested_q_{i}"):
        # Add the question to chat as if the user typed it
        add_to_chat_history("user", question)
        try:
            qa_chain = load_llm_chain()
            response = qa_chain.run({
                "phase": st.session_state.phase,
                "goal": st.session_state.support_goal,
                "diet": ", ".join(st.session_state.dietary_preferences),
                "question": question
            })
            add_to_chat_history("assistant", response)
            # If it's the first suggested question, store the response for download
            if i == 0:
                st.session_state["recommendations_response"] = response
            st.rerun()
        except Exception as e:
            st.error(f"Error: {str(e)}")

# After rendering chat bubbles, show download if available
def recommendations_to_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    # Add logo (centered)
    logo_path = "images/HerFoodCodeLOGO.png"
    pdf.image(logo_path, x=pdf.w/2-15, y=10, w=30)
    pdf.ln(25)
    # Title with color #442369
    pdf.set_text_color(68, 35, 105)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Your Nutritional overview per cycle phase", ln=True, align='C')
    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=12)
    for line in text.split('\n'):
        # Make section headers (lines starting with a number and dot) colored
        if line.strip().startswith(tuple(str(i)+'.' for i in range(1,10))):
            pdf.set_text_color(68, 35, 105)
            pdf.set_font("Arial", 'B', 12)
            pdf.multi_cell(0, 10, line)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", size=12)
        else:
            pdf.multi_cell(0, 10, line)
    return pdf.output(dest='S').encode('latin-1')

if st.session_state.get("recommendations_response"):
    st.markdown("### Download your recommendations")
    st.download_button(
        label="Download as PDF",
        data=recommendations_to_pdf(st.session_state["recommendations_response"]),
        file_name="cycle_phase_recommendations.pdf",
        mime="application/pdf"
    )
    st.download_button(
        label="Download as Text",
        data=st.session_state["recommendations_response"],
        file_name="cycle_phase_recommendations.txt",
        mime="text/plain"
    )

# --- Feedback Box at the bottom of the sidebar ---
st.sidebar.markdown("---")
st.sidebar.markdown("## Feedback")
feedback_text = st.sidebar.text_area("Have feedback or a question I didn't answer?", key="feedback_text")
if st.sidebar.button("Submit Feedback", key="submit_feedback"):
    if feedback_text.strip():
        feedback_data = {
            "user_id": st.session_state.get("user_id", "guest"),
            "timestamp": datetime.utcnow().isoformat(),
            "feedback": feedback_text.strip()
        }
        try:
            supabase.table("feedback").insert(feedback_data).execute()
            st.sidebar.success("Thank you for your feedback!")
            st.session_state["feedback_text"] = ""
        except Exception as e:
            st.sidebar.error(f"Error submitting feedback: {str(e)}")
    else:
        st.sidebar.warning("Please enter your feedback before submitting.")
