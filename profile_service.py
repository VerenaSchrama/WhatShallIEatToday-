import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from supabase import create_client
from config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPPORT_OPTIONS,
    DIETARY_OPTIONS,
    CYCLE_PHASES,
    ERROR_MESSAGES,
    SUCCESS_MESSAGES
)
from logging_service import LoggingService

class ProfileService:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        self.logger = LoggingService()

    def get_profile(self, user_id: str) -> Tuple[bool, Dict, str]:
        try:
            response = self.supabase.table("profiles").select("*").eq("user_id", user_id).execute()
            if not response.data:
                self.logger.log_db_event('profile_get', 'profiles', False, {'error': 'profile_not_found'})
                return False, {}, "Profile not found"

            profile = response.data[0]
            self.logger.log_db_event('profile_get', 'profiles', True)
            return True, profile, "Profile retrieved successfully"

        except Exception as e:
            self.logger.log_db_event('profile_get', 'profiles', False, {'error': str(e)})
            return False, {}, f"Error retrieving profile: {str(e)}"

    def update_profile(self, user_id: str, updates: Dict) -> Tuple[bool, str]:
        try:
            # Validate updates
            if 'phase' in updates and updates['phase'] not in CYCLE_PHASES:
                return False, "Invalid cycle phase"
            if 'goal' in updates and updates['goal'] not in SUPPORT_OPTIONS:
                return False, "Invalid support goal"
            if 'diet' in updates and not all(diet in DIETARY_OPTIONS for diet in updates['diet']):
                return False, "Invalid dietary preference"

            # Add updated_at timestamp
            updates['updated_at'] = datetime.utcnow().isoformat()

            response = self.supabase.table("profiles").update(updates).eq("user_id", user_id).execute()
            if not response.data:
                self.logger.log_db_event('profile_update', 'profiles', False, {'error': 'update_failed'})
                return False, "Failed to update profile"

            self.logger.log_db_event('profile_update', 'profiles', True)
            return True, "Profile updated successfully"

        except Exception as e:
            self.logger.log_db_event('profile_update', 'profiles', False, {'error': str(e)})
            return False, f"Error updating profile: {str(e)}"

    def export_user_data(self, user_id: str) -> Tuple[bool, Dict, str]:
        try:
            # Get user profile
            profile_response = self.supabase.table("profiles").select("*").eq("user_id", user_id).execute()
            if not profile_response.data:
                return False, {}, "Profile not found"

            # Get chat history
            chat_response = self.supabase.table("chat_history").select("*").eq("user_id", user_id).execute()

            # Get user info
            user_response = self.supabase.table("users").select("email, created_at, last_login").eq("id", user_id).execute()
            if not user_response.data:
                return False, {}, "User not found"

            # Compile export data
            export_data = {
                "profile": profile_response.data[0],
                "chat_history": chat_response.data,
                "user_info": {
                    "email": user_response.data[0]["email"],
                    "created_at": user_response.data[0]["created_at"],
                    "last_login": user_response.data[0]["last_login"]
                },
                "export_date": datetime.utcnow().isoformat()
            }

            self.logger.log_db_event('data_export', 'all', True)
            return True, export_data, "Data exported successfully"

        except Exception as e:
            self.logger.log_db_event('data_export', 'all', False, {'error': str(e)})
            return False, {}, f"Error exporting data: {str(e)}"

    def delete_account(self, user_id: str) -> Tuple[bool, str]:
        try:
            # Delete chat history
            self.supabase.table("chat_history").delete().eq("user_id", user_id).execute()

            # Delete profile
            self.supabase.table("profiles").delete().eq("user_id", user_id).execute()

            # Delete user
            self.supabase.table("users").delete().eq("id", user_id).execute()

            self.logger.log_db_event('account_deletion', 'all', True)
            return True, "Account deleted successfully"

        except Exception as e:
            self.logger.log_db_event('account_deletion', 'all', False, {'error': str(e)})
            return False, f"Error deleting account: {str(e)}"

    def get_chat_history(self, user_id: str, limit: int = 50) -> Tuple[bool, List, str]:
        try:
            response = self.supabase.table("chat_history").select("*").eq("user_id", user_id).order("timestamp", desc=True).limit(limit).execute()
            self.logger.log_db_event('chat_history_get', 'chat_history', True)
            return True, response.data, "Chat history retrieved successfully"

        except Exception as e:
            self.logger.log_db_event('chat_history_get', 'chat_history', False, {'error': str(e)})
            return False, [], f"Error retrieving chat history: {str(e)}"

    def clear_chat_history(self, user_id: str) -> Tuple[bool, str]:
        try:
            self.supabase.table("chat_history").delete().eq("user_id", user_id).execute()
            self.logger.log_db_event('chat_history_clear', 'chat_history', True)
            return True, "Chat history cleared successfully"

        except Exception as e:
            self.logger.log_db_event('chat_history_clear', 'chat_history', False, {'error': str(e)})
            return False, f"Error clearing chat history: {str(e)}" 