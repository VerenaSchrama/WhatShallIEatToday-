import streamlit as st
import json
from datetime import datetime
from profile_service import ProfileService
from config import (
    SUPPORT_OPTIONS,
    DIETARY_OPTIONS,
    CYCLE_PHASES,
    SUCCESS_MESSAGES,
    ERROR_MESSAGES
)

def render_profile_settings(profile_service: ProfileService, user_id: str):
    st.subheader("Profile Settings")
    
    # Get current profile
    success, profile, msg = profile_service.get_profile(user_id)
    if not success:
        st.error(msg)
        return

    # Create form for profile updates
    with st.form("profile_form"):
        # Cycle Phase
        current_phase = profile.get("phase", "")
        new_phase = st.selectbox(
            "Current Cycle Phase",
            options=[""] + CYCLE_PHASES,
            index=CYCLE_PHASES.index(current_phase) + 1 if current_phase in CYCLE_PHASES else 0
        )

        # Support Goal
        current_goal = profile.get("goal", "")
        new_goal = st.selectbox(
            "Support Goal",
            options=[""] + SUPPORT_OPTIONS,
            index=SUPPORT_OPTIONS.index(current_goal) + 1 if current_goal in SUPPORT_OPTIONS else 0
        )

        # Dietary Preferences
        current_diet = profile.get("diet", [])
        new_diet = st.multiselect(
            "Dietary Preferences",
            options=DIETARY_OPTIONS,
            default=current_diet
        )

        # Submit button
        submitted = st.form_submit_button("Update Profile")
        if submitted:
            updates = {}
            if new_phase:
                updates["phase"] = new_phase
            if new_goal:
                updates["goal"] = new_goal
            if new_diet:
                updates["diet"] = new_diet

            if updates:
                success, msg = profile_service.update_profile(user_id, updates)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

def render_data_management(profile_service: ProfileService, user_id: str):
    st.subheader("Data Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Export My Data"):
            success, data, msg = profile_service.export_user_data(user_id)
            if success:
                # Create a downloadable JSON file
                json_str = json.dumps(data, indent=2)
                st.download_button(
                    label="Download Data",
                    label_visibility="visible",
                    data=json_str,
                    file_name=f"cycle_nutrition_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            else:
                st.error(msg)

    with col2:
        if st.button("Clear Chat History"):
            if st.checkbox("I understand this action cannot be undone"):
                success, msg = profile_service.clear_chat_history(user_id)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

def render_account_management(profile_service: ProfileService, user_id: str):
    st.subheader("Account Management")
    
    if st.button("Delete Account"):
        st.warning("⚠️ This action cannot be undone!")
        if st.checkbox("I understand that all my data will be permanently deleted"):
            if st.text_input("Type 'DELETE' to confirm") == "DELETE":
                success, msg = profile_service.delete_account(user_id)
                if success:
                    st.success(msg)
                    st.session_state.logged_in = False
                    st.rerun()
                else:
                    st.error(msg)

def render_profile_page(profile_service: ProfileService, user_id: str):
    st.title("Profile Management")
    
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Profile Settings", "Data Management", "Account Management"])
    
    with tab1:
        render_profile_settings(profile_service, user_id)
    
    with tab2:
        render_data_management(profile_service, user_id)
    
    with tab3:
        render_account_management(profile_service, user_id) 