import re
import bcrypt
import uuid
from datetime import datetime, timedelta
import jwt
from supabase import create_client
from config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    SESSION_TIMEOUT,
    PASSWORD_MIN_LENGTH,
    ERROR_MESSAGES,
    SUCCESS_MESSAGES,
    VERIFICATION_TOKEN_EXPIRY,
    RESET_TOKEN_EXPIRY
)
from email_service import EmailService
from logging_service import LoggingService

class AuthService:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        self.email_service = EmailService()
        self.logger = LoggingService()
        self._validate_config()

    def _validate_config(self):
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise ValueError("Supabase configuration is missing")

    def _validate_email(self, email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def _validate_password(self, password: str) -> tuple[bool, str]:
        if len(password) < PASSWORD_MIN_LENGTH:
            return False, ERROR_MESSAGES["password_too_short"]
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        return True, ""

    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def _verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def _generate_session_token(self, user_id: str) -> str:
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(seconds=SESSION_TIMEOUT)
        }
        return jwt.encode(payload, SUPABASE_SERVICE_KEY, algorithm='HS256')

    def register_user(self, email: str, password: str) -> tuple[bool, str]:
        try:
            # Validate email
            if not self._validate_email(email):
                self.logger.log_auth_event('register', success=False, details={'error': 'invalid_email'})
                return False, ERROR_MESSAGES["invalid_email"]

            # Validate password
            is_valid, message = self._validate_password(password)
            if not is_valid:
                self.logger.log_auth_event('register', success=False, details={'error': 'invalid_password'})
                return False, message

            # Check if user exists
            response = self.supabase.table("users").select("*").eq("email", email).execute()
            if response.data:
                self.logger.log_auth_event('register', success=False, details={'error': 'user_exists'})
                return False, ERROR_MESSAGES["user_exists"]

            # Create user
            user_id = str(uuid.uuid4())
            hashed_pw = self._hash_password(password)
            
            self.supabase.table("users").insert({
                "id": user_id,
                "email": email,
                "password": hashed_pw,
                "email_verified": False,
                "created_at": datetime.utcnow().isoformat(),
                "last_login": None
            }).execute()

            # Send verification email
            email_sent = self.email_service.send_verification_email(user_id, email)
            if not email_sent:
                self.logger.log_email_event('verification', email, success=False)
                return False, ERROR_MESSAGES["email_send_failed"]

            self.logger.log_auth_event('register', user_id, success=True)
            self.logger.log_email_event('verification', email, success=True)
            return True, SUCCESS_MESSAGES["registration"]

        except Exception as e:
            self.logger.log_auth_event('register', success=False, details={'error': str(e)})
            return False, f"Registration error: {str(e)}"

    def login_user(self, email: str, password: str) -> tuple[bool, dict, str]:
        try:
            # Validate email
            if not self._validate_email(email):
                self.logger.log_auth_event('login', success=False, details={'error': 'invalid_email'})
                return False, None, ERROR_MESSAGES["invalid_email"]

            # Get user
            response = self.supabase.table("users").select("*").eq("email", email).execute()
            if not response.data:
                self.logger.log_auth_event('login', success=False, details={'error': 'user_not_found'})
                return False, None, ERROR_MESSAGES["invalid_credentials"]

            user = response.data[0]
            
            # Check email verification
            if not user.get("email_verified", False):
                self.logger.log_auth_event('login', user["id"], success=False, details={'error': 'email_not_verified'})
                return False, None, ERROR_MESSAGES["email_verification_required"]
            
            # Verify password
            if not self._verify_password(password, user["password"]):
                self.logger.log_auth_event('login', user["id"], success=False, details={'error': 'invalid_password'})
                return False, None, ERROR_MESSAGES["invalid_credentials"]

            # Generate session token
            session_token = self._generate_session_token(user["id"])

            # Update last login
            self.supabase.table("users").update({
                "last_login": datetime.utcnow().isoformat()
            }).eq("id", user["id"]).execute()

            self.logger.log_auth_event('login', user["id"], success=True)
            return True, {
                "id": user["id"],
                "email": user["email"],
                "session_token": session_token
            }, SUCCESS_MESSAGES["login"]

        except Exception as e:
            self.logger.log_auth_event('login', success=False, details={'error': str(e)})
            return False, None, f"Login error: {str(e)}"

    def reset_password(self, email: str) -> tuple[bool, str]:
        try:
            if not self._validate_email(email):
                self.logger.log_auth_event('password_reset', success=False, details={'error': 'invalid_email'})
                return False, ERROR_MESSAGES["invalid_email"]

            response = self.supabase.table("users").select("*").eq("email", email).execute()
            if not response.data:
                self.logger.log_auth_event('password_reset', success=False, details={'error': 'user_not_found'})
                return False, ERROR_MESSAGES["invalid_credentials"]

            user = response.data[0]
            email_sent = self.email_service.send_password_reset_email(user["id"], email)
            
            if not email_sent:
                self.logger.log_email_event('password_reset', email, success=False)
                return False, ERROR_MESSAGES["email_send_failed"]

            self.logger.log_auth_event('password_reset', user["id"], success=True)
            self.logger.log_email_event('password_reset', email, success=True)
            return True, SUCCESS_MESSAGES["password_reset"]

        except Exception as e:
            self.logger.log_auth_event('password_reset', success=False, details={'error': str(e)})
            return False, f"Password reset error: {str(e)}"

    def verify_session(self, session_token: str) -> tuple[bool, str]:
        try:
            payload = jwt.decode(session_token, SUPABASE_SERVICE_KEY, algorithms=['HS256'])
            self.logger.log_auth_event('session_verify', payload['user_id'], success=True)
            return True, payload['user_id']
        except jwt.ExpiredSignatureError:
            self.logger.log_auth_event('session_verify', success=False, details={'error': 'session_expired'})
            return False, ERROR_MESSAGES["session_expired"]
        except jwt.InvalidTokenError:
            self.logger.log_auth_event('session_verify', success=False, details={'error': 'invalid_token'})
            return False, "Invalid session token"

    def verify_email(self, token: str) -> tuple[bool, str]:
        try:
            success, user_id, token_type = self.email_service.verify_token(token)
            if not success or token_type != 'verification':
                self.logger.log_auth_event('email_verify', success=False, details={'error': 'invalid_token'})
                return False, ERROR_MESSAGES["invalid_token"]

            self.supabase.table("users").update({
                "email_verified": True
            }).eq("id", user_id).execute()

            self.logger.log_auth_event('email_verify', user_id, success=True)
            return True, SUCCESS_MESSAGES["email_verified"]

        except Exception as e:
            self.logger.log_auth_event('email_verify', success=False, details={'error': str(e)})
            return False, f"Email verification error: {str(e)}"

    def change_password(self, token: str, new_password: str) -> tuple[bool, str]:
        try:
            success, user_id, token_type = self.email_service.verify_token(token)
            if not success or token_type != 'reset':
                self.logger.log_auth_event('password_change', success=False, details={'error': 'invalid_token'})
                return False, ERROR_MESSAGES["invalid_token"]

            # Validate new password
            is_valid, message = self._validate_password(new_password)
            if not is_valid:
                self.logger.log_auth_event('password_change', success=False, details={'error': 'invalid_password'})
                return False, message

            # Update password
            hashed_pw = self._hash_password(new_password)
            self.supabase.table("users").update({
                "password": hashed_pw
            }).eq("id", user_id).execute()

            self.logger.log_auth_event('password_change', user_id, success=True)
            return True, SUCCESS_MESSAGES["password_changed"]

        except Exception as e:
            self.logger.log_auth_event('password_change', success=False, details={'error': str(e)})
            return False, f"Password change error: {str(e)}" 