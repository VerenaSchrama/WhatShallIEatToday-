import streamlit as st
from datetime import datetime

# Custom global styling
st.markdown(
    """
    <style>
        .main {
            background-color: #fdf6f0 !important;
            color: #3e3e3e !important;
        }
        .stApp {
            background-color: #fdf6f0 !important;
        }
        header, footer, .css-1rs6os {
            background-color: transparent !important;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #4a2c2a !important;
        }
        .stButton>button {
            background-color: #e07a5f !important;
            color: white !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            padding: 0.5em 1em !important;
            border: none !important;
        }
        .stButton>button:hover {
            background-color: #d65a3f !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)


def render_cycle_questions():
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

    return has_cycle

def render_personalization_sidebar():
    st.sidebar.header("Personal settings")
    support_options = ["Nothing specific", "Hormonal balance and regular cycle", "Getting back my period", "More energy", "Acne", "Eat more nutritious in general", "Digestive health/ Metabolism boost"]
    st.session_state.support_goal = st.sidebar.selectbox("What would you like support with? ℹ️", support_options)

    dietary_options = ["Vegan", "Vegetarian", "Nut allergy", "Gluten free", "Lactose intolerance"]
    st.session_state.dietary_preferences = st.sidebar.multiselect("Do you follow any dietary guidelines? ℹ️", dietary_options)

    if st.session_state.support_goal and st.session_state.dietary_preferences and st.session_state.phase:
        st.session_state.personalization_completed = True

def render_suggested_questions():
    st.markdown("### 💬 Suggested questions you can ask:")
    questions = [
        ("What foods are best for my current cycle phase?", "suggestion_q1"),
        ("Give me an overview of the 4 cycles and the foods I should eat for my goal.", "suggestion_q2"),
        ("Give me a 3-day breakfast plan", "suggestion_q3"),
        ("Why is organic food important for my cycle?", "suggestion_q4"),
        (f"What nutritional seeds support my {st.session_state.phase} phase (seed syncing)?", "suggestion_q5")
    ]
    for question, key in questions:
        if st.button(question, key=key):
            st.session_state.user_question = question
            st.session_state.question_triggered = True
            st.rerun()

def render_personalization_summary():
    st.markdown("---")
    st.header("Your Personalization Summary")
    st.markdown(f"**Cycle phase:** {st.session_state.phase}")
    st.markdown(f"**Support goal:** {st.session_state.support_goal}")
    if st.session_state.dietary_preferences:
        st.markdown(f"**Dietary preferences:** {', '.join(st.session_state.dietary_preferences)}")
    else:
        st.markdown("**Dietary preferences:** None")
    st.markdown("---")

    # Show example questions here
    render_suggested_questions()

